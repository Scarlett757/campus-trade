from unicodedata import category

from models import ProductCategory,User
from exts import db
# 批量初始化数据库
# 初始化要在终端专门运行flask init_category
def init_product_category():
    categories=["数码电子","教辅材料","宿舍好物","服饰鞋包","体育器材","美妆护肤"]
    # ProductCategory(name=category)的意思是创建一个productcategory对象，名字是category，即新建一条名字为category的数据
    category_models=[ProductCategory(name=category) for category in categories]
    db.session.add_all(category_models)
    db.session.commit()
    print("商品信息分类初始化成功！")
