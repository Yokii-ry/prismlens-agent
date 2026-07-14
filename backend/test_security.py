from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

# ===== 测试 1：密码加密 & 验证 =====
print("=== 测试密码加密 ===")
raw_password = "my_secret_123"
hashed = hash_password(raw_password)
print(f"原始密码: {raw_password}")
print(f"加密后: {hashed}")

# 正确密码应该验证通过
print(f"正确密码验证结果: {verify_password(raw_password, hashed)}")  # 期望 True
# 错误密码应该验证失败
print(f"错误密码验证结果: {verify_password('wrong_password', hashed)}")  # 期望 False

# ===== 测试 2：JWT 生成 & 解析 =====
print("\n=== 测试 JWT ===")
token = create_access_token({"user_id": 123, "username": "yoki"})
print(f"生成的 token: {token}")

payload = decode_access_token(token)
print(f"解析出的 payload: {payload}")  # 期望能看到 user_id、username、exp

# ===== 测试 3：篡改 token 应该解析失败 =====
print("\n=== 测试篡改 token ===")
fake_token = token[:-5] + "xxxxx"  # 故意改掉最后几位
fake_payload = decode_access_token(fake_token)
print(f"篡改后的 token 解析结果: {fake_payload}")  # 期望 None