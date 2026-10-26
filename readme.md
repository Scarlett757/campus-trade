# 1.项目说明  
本项目采用flask框架，设计了用户模块、商品模块、订单模块、收藏模块、商户沟通模块以及AI智能推荐模块，基本实现了一个校园二手交易市场网站。下面是一些页面展示。  
![img.png](readme_png/img.png)  
![img_1.png](readme_png/img_1.png)  
![img_2.png](readme_png/img_2.png)  
![img_3.png](readme_png/img_3.png)  
![img_4.png](readme_png/img_4.png)  
![img_5.png](readme_png/img_5.png)  
![img_6.png](readme_png/img_6.png)  
# 2. 项目食用指南
首先，请确保您的开发环境已安装 **Python 3.10.19。**  
本项目的核心亮点在于集成了 AI 能力，因此您需要**先在本地搭建 Ollama 服务**，这是实现智能交互的关键基石。  
在启动项目前，**请重点关注 config.py 文件**。这里不仅是**数据库连接的配置中心**，也是用户注册功能的“总控台”——我们需要您在此处填入**正确的邮箱服务参数**，以便系统能够发送验证码，保障账户安全。    
## 这是一个持续生长中的项目。自动化测试用于保障核心链路稳定性，也欢迎您提出改进建议，让我们一起把它建设得更好。
# 3. 质量保障与自动化测试

核心链路测试计划、参数化用例集、缺陷报告、[本次测试总结](docs/qa/test-summary.md)和[面试复盘](docs/qa/interview-walkthrough.md)见 [`docs/qa/`](docs/qa/)。在 Windows/Conda 环境中可运行：

```powershell
conda run -n flask-env python -m pytest -q
```

GitHub Actions 会在 `main`/`master` 分支 push、PR 和手动触发时执行同一测试集。
# 最后，开源之路漫长且充满挑战，如果您喜欢这个项目，请不吝赐教，点亮一颗 Star ️ 吧！这将是开发者最温暖的慰藉。  