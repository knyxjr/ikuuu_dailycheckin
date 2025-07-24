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

# 配置URL（使用新域名）
login_url = 'https://ikuuu.de/auth/login'
check_url = 'https://ikuuu.de/user/checkin'
info_url = 'https://ikuuu.de/user/profile'

# 请求头
header = {
    'origin': 'https://ikuuu.de',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'content-type': 'application/x-www-form-urlencoded',
    'referer': 'https://ikuuu.de/auth/login'  # 增加referer，模拟真实浏览器行为
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
        
        # 检查登录结果（以接口返回的ret=1作为登录成功标志）
        if login_result.get('ret') != 1:
            error_msg = login_result.get('msg', '未知错误')
            raise Exception(f"登录失败: {error_msg}")
        
        print("登录成功")

        # 2. 获取用户信息（弱化验证，仅作为辅助，不中断流程）
        print("\n2. 获取用户信息（非必需步骤）...")
        info_response = session.get(
            url=info_url,
            headers=header,
            timeout=15
        )
        print(f"用户信息请求状态码: {info_response.status_code}")
        # 打印部分响应（避免日志过长）
        print(f"用户信息响应部分内容: {info_response.text[:500]}")  # 只显示前500字符
        
        # 取消“用户中心”字符串验证（避免页面文字变化导致误判）
        # 改为宽松判断：只要状态码是200，就认为请求成功（即使内容有变化）
        if info_response.status_code != 200:
            print("警告: 用户信息请求失败，但继续执行签到（可能不影响）")
        else:
            print("用户信息请求成功（不验证页面内容）")
        
        # 尝试提取用户名（失败也不影响后续）
        username = "未知"
        try:
            # 调整正则（适配可能的页面结构变化）
            username_match = re.search(
                r'用户名[:：\s]*<span[^>]*>(.*?)</span>',  # 匹配“用户名: xxx”格式
                info_response.text, 
                re.I  # 忽略大小写
            )
            if not username_match:
                # 备选：匹配包含“user”的class（如原逻辑）
                username_match = re.search(r'<span class="user-[^>]*">(.*?)</span>', info_response.text, re.S)
            if username_match:
                username = username_match.group(1).strip()
                print(f"提取到用户名: {username}")
            else:
                print("提示: 未提取到用户名，不影响签到")
        except Exception as e:
            print(f"提取用户名时出错: {str(e)}（继续签到）")

        # 3. 执行签到（核心步骤）
        print("\n3. 开始签到...")
        check_response = session.post(
            url=check_url,
            headers=header,
            timeout=15
        )
        print(f"签到请求状态码: {check_response.status_code}")
        print(f"签到响应内容: {check_response.text}")  # 关键：查看实际签到结果
        
        check_response.raise_for_status()
        
        # 解析签到响应
        try:
            check_result = check_response.json()
        except json.JSONDecodeError:
            raise ValueError(f"签到响应不是有效的JSON格式: {check_response.text}")
        
        check_msg = check_result.get('msg', '签到结果未知')
        print(f"最终签到结果: {check_msg}")

        # 发送成功通知
        notify_title = f"ikuuu签到成功"
        notify_content = f"用户: {username}\n结果: {check_msg}"
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
