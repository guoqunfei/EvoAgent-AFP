# 1.大模型密钥配置
```
使用的deepseek的api
EvoAgent-AFP/backend/app/ai/features/APF-agent/AFP-agent.py
ALLBACK_API_KEY
```



# 2.网页版本运行
* 运行后端
```
cd EvoAgent-AFP/backend
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

* 运行前端
```
cd EvoAgent-AFP/frontend
npm install
npm run dev
```


* 查看已经存在的任务结果
在  会话ID 中输入 “20260706_060439_2fea6935” 回车


* 运行例子序列
点击 “AFP SEQUENCE” 模块右侧的demo, 然后在 “AFP Design Agent” 模块部分输入设计目标，“设计目标: 将TH活性提高3倍，同时保持或改善IRI活性”，回车或者点击发送按钮



# 3.命令行方式运行
* 切换目录与运行
```
cd EvoAgent-AFP/backend/app/ai/features/APF-agent
python3 main.py
```

* 输入内容：
```
序列: DTASDAAAAAALTAANAKAAAELTAANAAAAAAATAR
设计目标: 将TH活性提高3倍，同时保持或改善IRI活性
```



# 4.说明
目前只是一个Demo阶段，除了智能体比如像内存，一些系统提示词等需要有化外，工具部分尤其是虚拟实验模块需要后面添加工具，比如加入分子动力学模拟会显著提升可靠性，加入这个也就是在智能体中添加一个tool脚本，放在tools文件夹下面，运行分析动力学模拟需要有GPU环境和安装GROMACS等软件。但需要权衡精度与速度