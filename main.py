import requests
import json
import re
import os
from requests.exceptions import RequestException

# 初始化会话
session = requests.session()

# 从环境变量获取配置信息
email = os.environ.get('EMAIL')
passwd = os.environ.get('PASSWD')
SCKEY = os.environ.get('SCKEY')

# 配置URL
login_url = 'https://ikuuu.de/auth/login'
check_url = 'https://ikuuu.de/user/checkin'
info_url = 'https://ikuuu.de/user/profile'

# 请求头
header = {
    'origin': 'https://ikuuu.de',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'content-type': 'application/x-www-form-urlencoded'
}

# 登录数据
data = {
    'email': email,
    'passwd': passwd
}

def send_notification(title, content):
    """发送Server酱通知"""
    if SCKEY and SCKEY.strip():
        try:
            push_url = f'https://sctapi.ftqq.com/{SCKEY}.send'
            params = {
                'title': title,
                'desp': content
            }
            response = requests.post(push_url, params=params, timeout=10)
            response.raise_for_status()
            return True, "通知发送成功"
        except RequestException as e:
            return False, f"通知发送失败: {str(e)}"
    return False, "未配置SCKEY，不发送通知"

def main():
    # 打印初始配置信息（隐藏敏感内容）
    print("===== 初始化信息 =====")
    print(f"邮箱配置: {'已设置' if email else '未设置'}")
    print(f"密码配置: {'已设置' if passwd else '未设置'}")
    print(f"SCKEY配置: {'已设置' if SCKEY else '未设置'}")
    print("======================\n")

    try:
        # 1. 尝试登录
        print("1. 开始登录...")
        if not email or not passwd:
            raise ValueError("邮箱或密码未配置，请检查环境变量")

        login_response = session.post(
            url=login_url,
            headers=header,
            data=data,
            timeout=15  # 设置超时时间
        )
        
        # 打印登录响应状态
        print(f"登录请求状态码: {login_response.status_code}")
        print(f"登录响应内容: {login_response.text}")
        
        # 检查HTTP状态码
        login_response.raise_for_status()
        
        # 解析登录响应
        try:
            login_result = login_response.json()
        except json.JSONDecodeError:
            raise ValueError(f"登录响应不是有效的JSON格式: {login_response.text}")
        
        # 检查登录结果
        if login_result.get('ret') != 1:
            error_msg = login_result.get('msg', '未知错误')
            raise Exception(f"登录失败: {error_msg}")
        
        print("登录成功")

        # 2. 获取用户信息
        print("\n2. 获取用户信息...")
        info_response = session.get(
            url=info_url,
            headers=header,
            timeout=15
        )
        print(f"用户信息请求状态码: {info_response.status_code}")
        
        # 简单验证页面是否包含用户信息特征
        if '用户中心' not in info_response.text:
            raise Exception("获取用户信息失败，可能登录状态失效")
        
        # 提取用户名（尝试多种可能的选择器）
        username_match = re.search(r'<span class="user-name text-bold-600">(.*?)</span>', info_response.text, re.S)
        if username_match:
            username = username_match.group(1).strip()
            print(f"当前登录用户: {username}")
        else:
            print("警告: 未能提取用户名，但登录状态可能有效")

        # 3. 执行签到
        print("\n3. 开始签到...")
        check_response = session.post(
            url=check_url,
            headers=header,
            timeout=15
        )
        print(f"签到请求状态码: {check_response.status_code}")
        print(f"签到响应内容: {check_response.text}")
        
        check_response.raise_for_status()
        
        try:
            check_result = check_response.json()
        except json.JSONDecodeError:
            raise ValueError(f"签到响应不是有效的JSON格式: {check_response.text}")
        
        check_msg = check_result.get('msg', '签到结果未知')
        print(f"签到结果: {check_msg}")

        # 发送成功通知
        notify_title = f"ikuuu签到成功"
        notify_content = f"用户: {username if 'username' in locals() else '未知'}\n结果: {check_msg}"
        notify_success, notify_msg = send_notification(notify_title, notify_content)
        print(f"通知状态: {notify_msg}")

    except ValueError as ve:
        error_msg = f"参数或格式错误: {str(ve)}"
        print(f"错误: {error_msg}")
        send_notification("ikuuu签到失败-参数错误", error_msg)
    except RequestException as re:
        error_msg = f"网络请求错误: {str(re)}"
        print(f"错误: {error_msg}")
        send_notification("ikuuu签到失败-网络错误", error_msg)
    except Exception as e:
        error_msg = f"其他错误: {str(e)}"
        print(f"错误: {error_msg}")
        send_notification("ikuuu签到失败-其他错误", error_msg)

if __name__ == "__main__":
    main()
