# 登陆限制 比如没有登陆就不能发布商品信息
from flask import g,redirect
from functools import wraps

def login_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if g.user:
            return func(*args, **kwargs)
        else:
            return redirect('/login')
    return inner

# 为什么要import warp
# 有了wrap 再使用inner.__name__=func
# 路由是通过函数名和路由进行连接的


# 注意 下面这几行代码就相当于是把pub当成函数传递
# 效果：访问 /pub 时，会先执行 @login_required 的登录判断逻辑，再执行 pub 函数本身。
# @app.route('/pub')
# @login_required
# def pub():
#     pass