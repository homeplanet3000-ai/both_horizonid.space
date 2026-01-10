# BOT folder structure

```
bot
├── content
│   └── messages.json
├── database
│   ├── __init__.py
│   └── db.py
├── handlers
│   ├── __init__.py
│   ├── admin.py
│   ├── pay.py
│   └── user.py
├── keyboards
│   ├── inline.py
│   └── reply.py
├── load_tests
│   └── locustfile.py
├── middlewares
│   └── __init__.py
├── services
│   ├── __init__.py
│   ├── alerts.py
│   ├── content.py
│   ├── failover.py
│   ├── http.py
│   ├── marzban.py
│   ├── monitoring.py
│   ├── payment.py
│   ├── scheduler.py
│   └── servers.py
├── tests
│   ├── conftest.py
│   ├── test_handlers.py
│   └── test_payment_pipeline.py
├── utils
│   ├── misc.py
│   ├── states.py
│   └── text.py
├── bot_users.db
├── config.py
├── Dockerfile
├── main.py
├── requirements-dev.txt
└── requirements.txt
```
