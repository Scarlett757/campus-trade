import os

SECRET_KEY="shsjqjsbjqb"

BASE_DIR=os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR=os.path.join(BASE_DIR,'media')


MYSQL_HOST='localhost'
MYSQL_PORT=3306
MYSQL_USER='root'
MYSQL_PASSWORD='yanjing123456'
MYSQL_DATABASE='campus_trade'
SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

# 邮箱配置
MAIL_SERVER="smtp.qq.com"   # 邮件服务商 这里用的qq
MAIL_USE_SSL=True   # 使用ssl协议
MAIL_PORT=465
MAIL_USERNAME="3080259334@qq.com"
MAIL_PASSWORD="kcdrdbhvlzihdgja"    # 授权码
MAIL_DEFAULT_SENDER="3080259334@qq.com"