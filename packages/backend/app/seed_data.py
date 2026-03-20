"""
数据预置脚本 - 创建测试数据
"""
import random
from datetime import datetime, timedelta

from .database import db, Account, Token


def generate_mock_token():
    """生成模拟 Token"""
    import secrets
    return "sk-" + secrets.token_hex(24)


def seed_test_data():
    """
    预置测试数据
    """
    db.init()

    # 测试账号数据
    test_accounts = [
        {
            "platform": "openai",
            "email": "alice.test@gmail.com",
            "password": "Alice@2024!",
            "username": "alice_test",
            "first_name": "Alice",
            "last_name": "Johnson",
            "birth_year": 1995,
            "birth_month": 3,
            "birth_day": 15,
            "register_ip": "192.168.1.101",
            "status": "active",
            "verified": True,
        },
        {
            "platform": "openai",
            "email": "bob.developer@outlook.com",
            "password": "Bob#Secure123",
            "username": "bob_dev",
            "first_name": "Bob",
            "last_name": "Smith",
            "birth_year": 1990,
            "birth_month": 7,
            "birth_day": 22,
            "register_ip": "192.168.1.102",
            "status": "active",
            "verified": True,
        },
        {
            "platform": "openai",
            "email": "charlie.ai@yahoo.com",
            "password": "Charlie2024$",
            "username": "charlie_ai",
            "first_name": "Charlie",
            "last_name": "Brown",
            "birth_year": 1988,
            "birth_month": 11,
            "birth_day": 8,
            "register_ip": "192.168.1.103",
            "status": "active",
            "verified": True,
        },
        {
            "platform": "openai",
            "email": "diana.code@hotmail.com",
            "password": "Diana!Pass99",
            "username": "diana_code",
            "first_name": "Diana",
            "last_name": "Williams",
            "birth_year": 1992,
            "birth_month": 5,
            "birth_day": 30,
            "register_ip": "192.168.1.104",
            "status": "banned",
            "verified": True,
        },
        {
            "platform": "openai",
            "email": "evan.tech@gmail.com",
            "password": "Evan@Tech2024",
            "username": "evan_tech",
            "first_name": "Evan",
            "last_name": "Davis",
            "birth_year": 1998,
            "birth_month": 9,
            "birth_day": 12,
            "register_ip": "192.168.1.105",
            "status": "active",
            "verified": False,
        },
        {
            "platform": "claude",
            "email": "fiona.claude@gmail.com",
            "password": "Fiona#Claude1",
            "username": "fiona_ai",
            "first_name": "Fiona",
            "last_name": "Miller",
            "birth_year": 1994,
            "birth_month": 2,
            "birth_day": 28,
            "register_ip": "192.168.1.106",
            "status": "active",
            "verified": True,
        },
    ]

    created_accounts = 0
    created_tokens = 0

    with db.get_session() as session:
        for acc_data in test_accounts:
            # 检查账号是否已存在
            existing = session.query(Account).filter(
                Account.platform == acc_data["platform"],
                Account.email == acc_data["email"]
            ).first()

            if existing:
                print(f"账号已存在，跳过: {acc_data['email']}")
                continue

            # 创建账号
            account = Account(
                platform=acc_data["platform"],
                email=acc_data["email"],
                password=acc_data["password"],
                username=acc_data["username"],
                first_name=acc_data["first_name"],
                last_name=acc_data["last_name"],
                birth_year=acc_data["birth_year"],
                birth_month=acc_data["birth_month"],
                birth_day=acc_data["birth_day"],
                register_ip=acc_data["register_ip"],
                status=acc_data["status"],
                verified=acc_data["verified"],
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            )
            session.add(account)
            created_accounts += 1
            print(f"已创建账号: {acc_data['email']}")

            # 为 active 且 verified 的账号创建 Token
            if acc_data["status"] == "active" and acc_data["verified"]:
                safe_email = acc_data["email"].replace("@", "_at_").replace(".", "_")
                token_id = f"{acc_data['platform']}_{safe_email}"

                # 检查 Token 是否已存在
                existing_token = session.query(Token).filter(Token.token_id == token_id).first()
                if existing_token:
                    print(f"Token 已存在，跳过: {acc_data['email']}")
                    continue

                token = Token(
                    token_id=token_id,
                    platform=acc_data["platform"],
                    email=acc_data["email"],
                    access_token=generate_mock_token(),
                    refresh_token=generate_mock_token(),
                    id_token=generate_mock_token(),
                    token_type="Bearer",
                    expires_in=3600,
                    status="active",
                    used_count=random.randint(0, 50),
                    last_used=datetime.utcnow() - timedelta(hours=random.randint(1, 72)) if random.random() > 0.3 else None,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                )
                session.add(token)
                created_tokens += 1
                print(f"已创建 Token: {acc_data['email']}")

    print(f"\n数据预置完成: 创建 {created_accounts} 个账号, {created_tokens} 个 Token")
    return created_accounts, created_tokens


def clear_test_data():
    """清除所有测试数据"""
    db.init()

    with db.get_session() as session:
        session.query(Account).delete()
        session.query(Token).delete()

    print("测试数据已清除")


if __name__ == "__main__":
    seed_test_data()
