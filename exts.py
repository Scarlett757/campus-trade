from flask_sqlalchemy import  SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from flask_migrate import Migrate
from flask_mail import Mail
from sqlalchemy import event


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        # ix:index 索引   命名规则 → ix_字段名
        "ix": 'ix_%(column_0_label)s',
        # un unique 唯一约束    命名规则 → uq_表名_字段名
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        # ck: check 检查约束    命名规则 → ck_表名_约束名
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        # fk: foreign key 外键约束  命名规则 → fk_表名_字段名_关联表名
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        # pk primary key    命名规则 → pk_表名
        "pk": "pk_%(table_name)s"
    })
db=SQLAlchemy(model_class=Base)
migrate=Migrate() # 自动跟踪你对模型（表结构）的修改，并生成对应的 SQL 脚本，让数据库表结构和代码中的模型保持同步。
mail=Mail()

