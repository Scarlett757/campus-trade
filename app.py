from urllib.request import proxy_bypass

from flask import Flask, render_template, request, jsonify, session, redirect,g,send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, MetaData, Integer, String, desc, ForeignKey, Table, Column, Date, Text, Float, DateTime,select,and_,or_
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship, Mapped
import config
from exts import db,migrate,mail
from models import User,Product,ProductCategory,EmailCode,Favorite,Order,OrderMessage,OrderStatus,Address
from flask_mail import Message  # 发送邮件要先创建message对象
import random
import string
from datetime import datetime,timedelta
import commands
from decorators import login_required
import os
import uuid # 用于图片命名 随机产生
from ollama import chat
import json
import re
app = Flask(__name__)
app.config.from_object(config)

db.init_app(app)
migrate.init_app(app,db)
mail.init_app(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


# 创建命令：给 Flask 项目注册一个名为 init_category 的自定义命令,在终端执行 flask init_category 时，就会自动运行 commands.init_product_category 函数（也就是初始化蔬菜分类的函数）。
app.cli.command("init_category")(commands.init_product_category)
@app.before_request
def before_request():
    # 在每次请求到达视图函数前，自动从 session 中获取用户登录状态，并把用户信息绑定到 g 对象上，让所有视图函数都能直接用当前登录用户的信息。
    # 做网站时，每个页面都需要知道 “当前是谁在访问”（比如登录后显示用户名，未登录显示 “登录 / 注册”）。如果在每个路由里都写 “从 session 取 user_id → 查用户 → 赋值”，会重复大量代码；用 @app.before_request 这个钩子，只写一次，所有路由都能直接用 g.user 获取当前用户
    user_id=session.get('user_id')
    if user_id:
        user=db.session.get(User,user_id)
        # g 是线程级全局变量
        g.user=user
    else:
        g.user=None
# 你之前写的 @app.before_request 是 “请求前查用户，存在 g 里”，现在的 @app.context_processor 是 “渲染模板时，把 g.user 自动传给所有模板”，两者配合是 Flask 处理登录用户的 “黄金组合”
# 两个装饰器，一个装饰器存用户信息；一个装饰器负责把用户信息返回给所有页面
@app.context_processor
def context_processor():
    categories=db.session.scalars(db.select(ProductCategory)).all()
    # 给所有模板注入一个名为 user 的全局变量，值是 g.user（当前登录用户）；
    # 如果用户未登录，user 就是 None
    return{
        'user':g.user,
    # 注意 每一个要重复用的变量都应该返回
        'categories':categories
    }


@app.route('/')
def index():
    # 1. 获取页码 (默认第1页)
    page = request.args.get('page', 1, type=int)

    # 2. 获取每页显示的数量
    per_page = 8

    # 3. 获取分类筛选参数
    category_id = request.args.get('category', type=int)

    # 4. 构建基础查询语句
    if category_id:
        stmt = db.select(Product).where(Product.category_id == category_id)
    else:
        stmt = db.select(Product)

    # 5. 执行分页查询
    pagination = db.paginate(
        stmt.order_by(Product.pub_date.desc()),
        page=page,
        per_page=per_page,
        error_out=False
    )

    # 6. 提取当前页商品列表
    products = pagination.items

    # 7. 获取所有分类
    categories = db.session.scalars(db.select(ProductCategory)).all()

    if g.user:
        # 使用 scalars 直接获取 ID 列表
        favorite_product_ids = db.session.scalars(
            select(Favorite.product_id).where(Favorite.user_id == g.user.id)
        ).all()
    else:
        favorite_product_ids = []

    return render_template(
        'index.html',
        products=products,
        pagination=pagination,
        categories=categories,
        category_id=category_id,
        # ✅ 确保传递的是列表
        favorite_product_ids=favorite_product_ids
    )
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == "GET":
        return render_template('login.html')
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember')
        user=db.session.scalar(db.select(User).where(User.email == email))
        if user and user.check_password(password):
            session['user_id']=user.id
            if remember:
                # 设置permannent=True，那么31天后会过期
                session.permanent=True
            return redirect("/")
        else:
            print("邮箱或密码错误")
            return redirect("/login")
@app.post('/logout')
def logout():
    session.clear()
    return redirect("/")
@app.route('/profile',methods=['GET','POST'])
@login_required
def profile():
    # 查询当前用户发布的所有商品
    things = db.session.scalars(
        db.select(Product).where(Product.publisher_id == g.user.id).order_by(Product.pub_date.desc())
    ).all()

    if request.method == "GET":
        return render_template('profile.html', things=things, user=g.user)

    elif request.method == "POST":
        try:
            # 1. 获取文本数据
            mobile = request.form.get('mobile', '').strip()
            signature = request.form.get('signature', '').strip()

            # 简单验证
            if mobile and not mobile.isdigit():
                return jsonify({"message": "手机号格式不正确"}), 400
            if len(mobile) > 0 and len(mobile) != 11:
                return jsonify({"message": "手机号必须是11位数字"}), 400

            # 2. 处理头像上传
            avatar_file = request.files.get('avatar')
            new_avatar_path = g.user.avatar  # 默认保持原头像

            if avatar_file and avatar_file.filename != '':
                if not allowed_file(avatar_file.filename):
                    return jsonify({"message": "只允许上传 jpg, png, gif 格式的图片"}), 400

                # 生成唯一文件名
                ext = avatar_file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"

                # 确保上传目录存在 (根据你的实际路径调整)
                upload_folder = os.path.join('media')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)

                save_path = os.path.join(upload_folder, filename)
                avatar_file.save(save_path)

                # 构造数据库存储的路径 (与 pub.html 逻辑一致，存完整访问路径)
                new_avatar_path = f"/media/{filename}"

            # 3. 更新数据库
            g.user.mobile = mobile if mobile else None
            g.user.signature = signature if signature else None
            g.user.avatar = new_avatar_path

            db.session.commit()

            return jsonify({"message": "更新成功", "avatar": new_avatar_path}), 200

        except Exception as e:
            db.session.rollback()
            print(f"Profile update error: {e}")
            return jsonify({"message": "服务器内部错误，请稍后重试"}), 500


@app.route('/pub', methods=['GET', 'POST'])
@login_required
def pub():
    if request.method == "GET":
        categories = db.session.scalars(db.select(ProductCategory)).all()
        return render_template('pub.html', categories=categories)
    else:
        try:
            # 1. 获取所有表单字段 (原始数据)
            picture = request.form.get('picture', '').strip()
            category_input = request.form.get('category')  # 可能是数字ID，也可能是 "new_category"
            new_category_name = request.form.get('new_category_name', '').strip()

            name = request.form.get('name', '').strip()
            content = request.form.get('content', '').strip()
            price_str = request.form.get('price', '').strip()
            num_str = request.form.get('num', '').strip()
            origin_place = request.form.get('origin_place', '').strip()
            ship_name = request.form.get('ship_name', '').strip()
            mobile = request.form.get('mobile', '').strip()

            # 2. 基础非空验证 (注意：这里只验证原始输入 category_input，不验证 category_id)
            if not category_input:
                return "错误：请选择一个分类！", 400

            # 如果用户选择了“新增分类”，则必须填写新分类名称
            if category_input == "new_category" and not new_category_name:
                return "错误：您选择了新增分类，但未输入分类名称！", 400

            required_fields = {
                "物品名称": name,
                "详细描述": content,
                "价格": price_str,
                "数量": num_str,
                "发货地点": origin_place,
                "发货方式": ship_name,
                "联系电话": mobile
            }

            for field_name, field_value in required_fields.items():
                if not field_value:
                    return f"错误：{field_name}不能为空！", 400

            if not picture:
                return "错误：请至少上传一张物品图片！", 400

            # 3. 【核心修复】在此处计算最终的 category_id
            category_id = None

            if category_input == "new_category":
                # --- 场景 A: 用户选择新增分类 ---
                # 查重：忽略大小写
                existing_cate = db.session.scalar(
                    db.select(ProductCategory).where(
                        db.func.lower(ProductCategory.name) == new_category_name.lower()
                    )
                )

                if existing_cate:
                    category_id = existing_cate.id
                    print(f"分类 '{new_category_name}' 已存在，使用 ID: {category_id}")
                else:
                    # 创建新分类
                    new_cate_obj = ProductCategory(name=new_category_name)
                    db.session.add(new_cate_obj)
                    db.session.flush()  # 获取 ID 但不提交
                    category_id = new_cate_obj.id
                    print(f"创建新分类 '{new_category_name}', ID: {category_id}")

            else:
                # --- 场景 B: 用户选择现有分类 ---
                try:
                    category_id = int(category_input)
                except ValueError:
                    return "错误：分类 ID 格式无效！", 400

                # 验证 ID 是否存在
                cate_exists = db.session.get(ProductCategory, category_id)
                if not cate_exists:
                    return "错误：选择的分类不存在！", 400

            # 4. 类型转换（价格和数量）
            try:
                price = float(price_str)
                num = int(num_str)
                if price < 0 or num < 1:
                    return "错误：价格不能为负，数量至少为 1！", 400
            except ValueError:
                return "错误：价格或数量格式不正确！", 400

            # 5. 创建物品对象 (此时 category_id 已经肯定有值了)
            product = Product(
                name=name,
                content=content,
                price=price,
                num=num,
                picture=picture,
                origin_place=origin_place,
                ship_name=ship_name,
                category_id=category_id,
                publisher_id=g.user.id,
            )

            db.session.add(product)
            db.session.commit()

            return redirect("/")

        except Exception as e:
            db.session.rollback()
            print(f"发布失败 - 真实错误：{str(e)}")
            import traceback
            traceback.print_exc()
            return f"发布失败：{str(e)}", 500

@app.post("/upload/picture")
def upload_picture():
    # 让用户上传图片的时候，图片的name为picture
    picture=request.files.get('picture')
    # 重新给图片命名
    # abc.jpg=>['abc','jpg']
    ext=picture.filename.split('.')[-1]
    filename=f"{uuid.uuid4()}.{ext}"
    picture_path=os.path.join(app.config['MEDIA_DIR'],filename)
    picture.save(picture_path)

    return jsonify({"result":True,"filename":filename})

@app.route("/media/<filename>")
def media(filename):
    return send_from_directory(app.config['MEDIA_DIR'],filename)


@app.route('/register',methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        email=request.form.get('email')
        username=request.form.get('username')
        password=request.form.get('password')
        code=request.form.get('code')
        code_model=db.session.scalar(db.select(EmailCode).where(EmailCode.email==email,EmailCode.code==code))
        if not code_model or (datetime.now()-code_model.create_time)>timedelta(minutes=30):
            return jsonify({"result":False,"message":"请输入正确的验证码"})
        user=User(email=email,username=username,password=password)
        db.session.add(user)
        db.session.commit()
        return jsonify({"result":True,"message":None})
@app.route('/detail/<int:product_id>')
def detail(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return "商品不存在", 404

    is_favorited = False

    if g.user:
        stmt = select(Favorite).where(
            Favorite.user_id == g.user.id,
            Favorite.product_id == product_id
        )
        favorite_record = db.session.scalar(stmt)
        if favorite_record:
            is_favorited = True
    categories = db.session.scalars(db.select(ProductCategory)).all()
    return render_template('detail.html',
                           product=product,
                           categories=categories,
                           is_favorited=is_favorited)

@app.get("/email/code")
def get_email_code():
    # 这段代码定义了一个 GET 类型的 API 接口，路径是 /email/code，核心功能是：接收前端传递的 email 参数，检查该参数是否为空；如果为空则返回失败提示，否则返回成功提示（这通常是 “发送邮箱验证码” 接口的第一步校验逻辑）
    # request.args 是 FastAPI 中获取 URL 问号后查询参数 的方式（比如 http://localhost:8000/email/code?email=test@163.com 中的 email=test@163.com）。
    email=request.args.get("email")
    if not email:
        return jsonify({"request":False,"message":"email is empty！"})
    # 生成验证码
    source=string.digits*4
    code="".join(random.sample(source,4))
    message=Message(
        subject="[新鲜菜园]注册验证码",
        recipients=[email],
        body=f"[新鲜菜园]注册验证码：{code}"
    )
    try:
        mail.send(message)
    except Exception as e:
        return jsonify({"request":False,"message":str(e)})
    # 实际生产环境中使用memcached/redis缓存这种五分钟就会过期的不重要数据
    code_model=EmailCode(code=code,email=email)
    db.session.add(code_model)
    db.session.commit()
    return jsonify({"request":True,"message":None})


@app.route('/favorite/toggle/<int:product_id>', methods=['POST'])
@login_required
def toggle_favorite(product_id):
    # 检查商品是否存在
    product = db.get_or_404(Product, product_id)

    # 查询是否已收藏
    stmt = select(Favorite).where(
        Favorite.user_id == g.user.id,
        Favorite.product_id == product_id
    )
    favorite = db.session.scalar(stmt)

    if favorite:
        # 如果已收藏 -> 取消收藏
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'success': True, 'action': 'removed', 'message': '已取消收藏'})
    else:
        # 如果未收藏 -> 加入收藏
        new_favorite = Favorite(user_id=g.user.id, product_id=product_id)
        db.session.add(new_favorite)
        db.session.commit()
        return jsonify({'success': True, 'action': 'added', 'message': '收藏成功'})


# 3. "我的收藏" 页面
@app.route('/favorites')
@login_required
def my_favorites():
    page = request.args.get('page', 1, type=int)
    per_page = 8

    # 查询当前用户收藏的商品列表 (通过关联表连接)
    stmt = select(Product).join(Favorite).where(Favorite.user_id == g.user.id)

    pagination = db.paginate(
        stmt.order_by(Favorite.created_at.desc()),  # 按收藏时间倒序
        page=page,
        per_page=per_page,
        error_out=False
    )

    products = pagination.items
    categories = db.session.scalars(db.select(ProductCategory)).all()

    return render_template('favorites.html',
                           products=products,
                           pagination=pagination,
                           categories=categories,
                           category_id=None)





def search_database(keyword, min_price=None, max_price=None):
    """
    增强版搜索：同时匹配 商品名、商品描述、分类名
    """
    try:
        # 基础查询：只查有库存的 (num > 0)
        query = Product.query.filter(Product.num > 0)

        if keyword:
            k = f"%{keyword}%"

            # 2. 使用正确的类名 ProductCategory 进行 join
            # 关系名是 'category' (在 Product 模型中定义: category: Mapped[ProductCategory])
            query = query.join(ProductCategory).filter(
                or_(
                    Product.name.like(k),  # 匹配商品名 (如 "二手电动车")
                    Product.content.like(k),  # 匹配描述 (如 "出售自用电动车")
                    ProductCategory.name.like(k)  # 3. 匹配分类名 (使用正确的类名)
                )
            )
            print(f"🔍 SQL 过滤条件：关键词 '{keyword}'")

        # 价格过滤
        if min_price is not None:
            query = query.filter(Product.price >= float(min_price))
        if max_price is not None:
            query = query.filter(Product.price <= float(max_price))

        # 执行查询，限制返回 5 条
        results = query.limit(5).all()

        # --- 调试日志 ---
        if not results:
            print(f"⚠️ 未找到商品！当前关键词：{keyword}")
            # 打印所有商品名，帮你排查数据库里到底叫啥
            all_prods = Product.query.all()
            print(f"💡 数据库里所有的商品名: {[p.name for p in all_prods]}")
            # 打印所有分类名
            all_cats = ProductCategory.query.all()
            print(f"💡 数据库里所有的分类名: {[c.name for c in all_cats]}")
        else:
            print(f"✅ 成功找到 {len(results)} 个商品")

        # 构造返回数据
        data = [{
            "name": p.name,
            "price": p.price,
            "desc": p.content[:50] + "..." if p.content and len(p.content) > 50 else (p.content or "无描述"),
            "id": p.id,
            "image": p.picture,
            "category": p.category.name if p.category else "未知分类"
        } for p in results]

        return json.dumps(data, ensure_ascii=False)

    except Exception as e:
        print(f"❌ 数据库查询出错: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({"error": str(e)})


@app.route('/api/chat', methods=['POST'])
def ai_chat():
    user_message = request.json.get('message')

    # --- 系统提示词：更严格的指令 ---
    system_prompt = """
    你是校园二手集市助手。
    任务：判断用户是否想查找商品。

    规则：
    1. 如果用户提到具体商品（如“电动车”、“相机”、“书”），请 ONLY 返回以下 JSON 格式，不要任何多余文字、标点或解释：
    {"action": "search", "keyword": "关键词", "min_price": null, "max_price": null}
    2. 价格如果用户没说，必须设为 null。
    3. 关键词只保留核心名词（如“电动车”而不是“二手电动车”）。
    4. 如果是闲聊，直接回答。
    """

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_message}
    ]

    try:
        # --- 第一轮：获取意图 (保持不变) ---
        response = chat(
            model='llama3:8b-instruct-q4_0',
            messages=messages,
            options={'temperature': 0.1}
        )

        raw_content = response.message.content.strip()
        print(f"🤖 AI 原始回复: {raw_content}")

        # --- 正则提取 JSON (保持不变) ---
        json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)

        if json_match:
            json_str = json_match.group()
            try:
                data = json.loads(json_str)

                if data.get('action') == 'search':
                    keyword = data.get('keyword')
                    min_p = data.get('min_price')
                    max_p = data.get('max_price')

                    print(f"🔍 执行搜索: {keyword}, {min_p}-{max_p}")

                    # 1. 执行数据库查询
                    db_result_json = search_database(keyword, min_p, max_p)
                    db_result_list = json.loads(db_result_json)

                    print(f"📦 数据库返回结果数量: {len(db_result_list)}")
                    print(f"📦 数据库返回结果内容预览: {db_result_json[:100]}...")

                    # 2. 如果有结果，准备第二轮对话
                    messages.append({'role': 'assistant', 'content': raw_content})

                    if not db_result_list:
                        prompt_text = "数据库没找到相关商品。请礼貌地告知用户没找到，并建议换个关键词试试。"
                    else:
                        # 构造上下文数据
                        context_data = json.dumps(db_result_list, ensure_ascii=False)
                        prompt_text = f"""
                        你是一个友好的校园二手集市助手。
                        用户想查找：{keyword}

                        系统已从数据库找到以下商品 (JSON格式)：
                        {context_data}

                        任务：
                        1. 根据找到的商品，用热情、自然的语气回复用户。
                        2. 列出商品名称和价格。
                        3. 简单提炼一个亮点（基于描述）。
                        4. 不要输出 JSON，只输出自然语言文本。
                        """

                    print(f"📝 构造第二轮 Prompt 长度: {len(prompt_text)}")

                    messages.append({'role': 'system', 'content': prompt_text})

                    # 3. 【关键】执行第二轮 AI 调用
                    try:
                        final_response = chat(
                            model='llama3:8b-instruct-q4_0',
                            messages=messages,
                            options={'temperature': 0.7}
                        )

                        final_text = final_response.message.content.strip()

                        print(f"✨ AI 原始返回内容: {final_text[:100]}...")

                        # 🚨【防御机制 + 链接生成】
                        # 如果 AI 不听话返回了 JSON，或者为了统一格式，我们直接用 Python 生成带链接的回复
                        if final_text.startswith('{') or '"action"' in final_text or True:
                            # 这里我把条件改成了 True (或者保留前面的判断)，意味着只要搜到商品，我们就用这个漂亮模板覆盖 AI 的回答，确保链接一定在

                            print("✨ 正在生成带跳转链接的标准回复...")

                            final_text = f"🎉 我帮你找到了 {len(db_result_list)} 个相关的「{keyword}」：\n\n"

                            for item in db_result_list:
                                # 构造详情链接
                                detail_url = f"/detail/{item['id']}"

                                # 拼接每一行：名字(价格) + 描述 + 链接
                                # 注意：这里我们直接嵌入 HTML <a> 标签
                                final_text += f"🔹 <b>{item['name']}</b> - ¥{item['price']}<br>"
                                final_text += f"   💬 {item['desc']}<br>"
                                final_text += f"   👉 <a href='{detail_url}' target='_blank' class='text-primary-600 underline font-bold hover:text-primary-800'>查看详情</a><br><br>"

                            final_text += "点击链接即可看到宝贝的详细信息和卖家联系方式哦！"

                            # 标记这条消息包含 HTML，前端需要特殊处理（见第二步）
                            # 我们在返回的 JSON 里加一个字段 is_html: true
                            return jsonify({
                                "reply": final_text,
                                "source": "database",
                                "products": db_result_list,
                                "is_html": True  # <--- 新增标记
                            })


                    except Exception as ai_err:
                        print(f"❌ 第二轮 AI 调用失败: {ai_err}")
                        import traceback
                        traceback.print_exc()
                        # 如果 AI 挂了，至少把数据库结果以简单文本返回，不要返回 JSON 指令
                        fallback_reply = f"找到了 {len(db_result_list)} 个相关商品，但稍后为您整理详情。"
                        return jsonify({
                            "reply": fallback_reply,
                            "source": "database_fallback",
                            "products": db_result_list
                        })

            except json.JSONDecodeError as e:
                print(f"⚠️ JSON 解析失败: {e}")
                # 解析失败，降级为闲聊
                pass

        # 如果不是搜索意图，或者上面所有逻辑都没命中，走这里
        print("💬 进入普通闲聊模式")
        return jsonify({"reply": raw_content, "source": "chat"})

    except Exception as e:
        print(f"💥 全局严重错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"reply": "系统开小差了，请稍后再试。"}), 500
# ==========================================
# 3. 前端页面 (简单的聊天窗口)
# ==========================================

@app.route('/assistant')
@login_required
def assistant_page():
    return render_template('assistant.html')  # 你需要创建这个模板


# 1. 获取用户地址列表
# 1. 获取当前用户的地址列表
@app.route('/api/address')
@login_required
def get_addresses():
    addresses = Address.query.filter_by(user_id=g.user.id).order_by(Address.is_default.desc(),
                                                                            Address.id.desc()).all()
    result = []
    for addr in addresses:
        result.append({
            'id': addr.id,
            'receiver': addr.receiver,
            'phone': addr.phone,
            'province': addr.province,
            'city': addr.city,
            'district': addr.district,
            'detail': addr.detail,
            'is_default': addr.is_default
        })
    return jsonify(result)


# 2. 新增地址
@app.route('/api/address', methods=['POST'])
@login_required
def add_address():
    data = request.json
    # 如果设为默认，先将该用户其他地址取消默认
    if data.get('is_default'):
        Address.query.filter_by(user_id=g.user.id, is_default=True).update({'is_default': False})

    new_addr = Address(
        user_id=g.user.id,
        receiver=data['receiver'],
        phone=data['phone'],
        province=data['province'],
        city=data['city'],
        district=data['district'],
        detail=data['detail'],
        is_default=data.get('is_default', False)
    )
    db.session.add(new_addr)
    db.session.commit()
    return jsonify({'success': True, 'id': new_addr.id})


# 3. 更新地址
@app.route('/api/address/<int:addr_id>', methods=['PUT'])
@login_required
def update_address(addr_id):
    addr = Address.query.get_or_404(addr_id)
    if addr.user_id != g.user.id:
        return jsonify({'error': '无权操作'}), 403

    data = request.json
    # 如果设为默认，先取消其他默认
    if data.get('is_default') and not addr.is_default:
        Address.query.filter_by(user_id=g.user.id, is_default=True).update({'is_default': False})

    addr.receiver = data['receiver']
    addr.phone = data['phone']
    addr.province = data['province']
    addr.city = data['city']
    addr.district = data['district']
    addr.detail = data['detail']
    addr.is_default = data.get('is_default', False)

    db.session.commit()
    return jsonify({'success': True})


# 4. 删除地址
@app.route('/api/address/<int:addr_id>', methods=['DELETE'])
@login_required
def delete_address(addr_id):
    addr = Address.query.get_or_404(addr_id)
    if addr.user_id != g.user.id:
        return jsonify({'error': '无权操作'}), 403

    db.session.delete(addr)
    db.session.commit()
    return jsonify({'success': True})


# 5. 设为默认地址
@app.route('/api/address/<int:addr_id>/default', methods=['POST'])
@login_required
def set_default_address(addr_id):
    addr = Address.query.get_or_404(addr_id)
    if addr.user_id != g.user.id:
        return jsonify({'error': '无权操作'}), 403

    # 事务处理：先取消所有默认，再设置当前
    Address.query.filter_by(user_id=g.user.id, is_default=True).update({'is_default': False})
    addr.is_default = True
    db.session.commit()

    return jsonify({'success': True})


# ✨ 新增：渲染订单列表页面
@app.route('/orders')
@login_required
def my_orders_page():
    return render_template('orders.html')


# 2. 创建订单 (核心)
@app.route('/api/order/create', methods=['POST'])
@login_required
def create_order():
    data = request.json
    product_id = data.get('product_id')
    address_id = data.get('address_id')

    if not product_id or not address_id:
        return jsonify({"error": "缺少商品或地址信息"}), 400

    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({"error": "商品不存在"}), 404

        if product.num < 1:
            return jsonify({"error": "库存不足，商品已售罄"}), 400

        # 👇 修改：检查是否是自己卖的商品
        if product.publisher_id == g.user.id:
            return jsonify({"error": "不能购买自己的商品"}), 400

        # 👇 修改：验证地址属于当前用户
        address = Address.query.filter_by(id=address_id, user_id=g.user.id).first()
        if not address:
            return jsonify({"error": "地址无效或不属于您"}), 400

        # 生成订单号
        order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"

        # 创建订单
        new_order = Order(
            order_no=order_no,
            buyer_id=g.user.id,
            seller_id=product.publisher_id,
            product_id=product.id,
            price=product.price,
            address_id=address.id,
            status=OrderStatus.PAID
        )

        # 扣减库存
        product.num -= 1

        db.session.add(new_order)
        db.session.commit()

        # 可选：给商家发一条系统消息通知
        sys_msg = OrderMessage(
            order_id=new_order.id,
            sender_id=g.user.id,
            content=f"用户 {g.user.username} 已下单，请尽快发货。",
            msg_type='system'
        )
        db.session.add(sys_msg)
        db.session.commit()

        return jsonify({
            "success": True,
            "order_id": new_order.id,
            "message": "下单成功！"
        })

    except Exception as e:
        db.session.rollback()
        print(f"❌ 下单失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "下单失败，请稍后重试"}), 500


# 3. 获取我的订单列表
@app.route('/api/orders', methods=['GET'])
@login_required
def get_my_orders():
    role = request.args.get('role', 'buyer')  # buyer 或 seller

    if role == 'seller':
        orders = Order.query.filter_by(seller_id=g.user.id).order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.filter_by(buyer_id=g.user.id).order_by(Order.created_at.desc()).all()

    result = []
    for o in orders:
        # 防止关联对象为空导致报错 (虽然逻辑上不应该空)
        p_name = o.product.name if o.product else "未知商品"
        p_img = o.product.picture if o.product else ""
        counterpart = o.seller.username if (role == 'buyer' and o.seller) else (
            o.buyer.username if (role == 'seller' and o.buyer) else "未知用户")

        result.append({
            "id": o.id,
            "order_no": o.order_no,
            "product_name": p_name,
            "product_image": p_img,
            "price": o.price,
            "status": o.status.value,
            "status_text": {
                'paid': '待发货',
                'shipped': '已发货',
                'completed': '已完成',
                'cancelled': '已取消'
            }.get(o.status.value, o.status.value),
            "created_at": o.created_at.strftime('%Y-%m-%d %H:%M'),
            "counterpart_name": counterpart,
            "has_new_message": False
        })

    return jsonify(result)


# 4. 商家发货
@app.route('/api/order/<int:order_id>/ship', methods=['POST'])
@login_required
def ship_order(order_id):

    order = Order.query.get_or_404(order_id)

    # 权限检查：只有卖家能发货
    if order.seller_id != g.user.id:
        return jsonify({"error": "无权操作，您不是该商品的卖家"}), 403

    if order.status != OrderStatus.PAID:
        return jsonify({"error": f"订单状态为 ({order.status.value})，不允许发货"}), 400

    order.status = OrderStatus.SHIPPED

    # 发送系统通知给买家
    notify_msg = OrderMessage(
        order_id=order.id,
        sender_id=g.user.id,
        content="商家已发货，请注意查收！",
        msg_type='system'
    )
    db.session.add(notify_msg)
    db.session.commit()

    return jsonify({"success": True, "message": "发货成功"})


# 5. 订单消息 (聊天/砍价)
@app.route('/api/order/<int:order_id>/messages', methods=['GET', 'POST'])
@login_required
def order_messages(order_id):
    order = Order.query.get_or_404(order_id)

    # 权限：只有买卖双方能看
    if order.buyer_id != g.user.id and order.seller_id != g.user.id:
        return jsonify({"error": "无权访问此订单消息"}), 403

    if request.method == 'POST':
        content = request.json.get('content')
        if not content:
            return jsonify({"error": "内容不能为空"}), 400

        msg = OrderMessage(
            order_id=order.id,
            sender_id=g.user.id,
            content=content,
            msg_type='text'
        )
        db.session.add(msg)
        db.session.commit()
        return jsonify({"success": True})

    else:  # GET
        msgs = OrderMessage.query.filter_by(order_id=order.id).order_by(OrderMessage.created_at.asc()).all()
        data = [{
            "sender": m.sender.username if m.sender else "未知",
            "sender_id": m.sender_id,
            "content": m.content,
            "type": m.msg_type,
            "time": m.created_at.strftime('%H:%M')
        } for m in msgs]
        return jsonify(data)

@app.route('/order/<int:order_id>/chat')
@login_required
def order_chat_page(order_id):
    return render_template('order_chat.html',order_id=order_id)



if __name__ == '__main__':
    app.run()