#!/usr/bin/env python3
"""
墨迹天气自动查询推送脚本
查询上海黄浦区、杭州余杭区在3月29日的天气
每天定时自动推送
"""

import os
import sys
import subprocess

# 自动安装依赖
def install_package(package):
    try:
        __import__(package)
    except ImportError:
        print(f"正在安装 {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])

install_package("requests")
install_package("beautifulsoup4")

import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 目标日期
TARGET_DATE = "3月29日"
TARGET_DAY = 29

# 墨迹天气URL配置
WEATHER_URLS = {
    "上海黄浦区": {
        "current": "https://tianqi.moji.com/weather/china/shanghai/huangpu-district",
        "forecast15": "https://tianqi.moji.com/forecast15/china/shanghai/huangpu-district"
    },
    "杭州余杭区": {
        "current": "https://tianqi.moji.com/weather/china/zhejiang/yuhang-district",
        "forecast15": "https://tianqi.moji.com/forecast15/china/zhejiang/yuhang-district"
    }
}

# 从环境变量读取 SendKey
PUSH_CONFIG = {
    "serverchan_key": os.environ.get("SERVERCHAN_KEY", "")
}


def fetch_weather(city_name, urls):
    """抓取指定城市的天气信息"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        weather_data = {
            "city": city_name,
            "current_temp": "",
            "current_condition": "",
            "humidity": "",
            "wind": "",
            "forecast_29": None,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        # 1. 获取当前天气（从主页面）
        current_url = urls.get("current", urls) if isinstance(urls, dict) else urls
        response = requests.get(current_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取当前天气信息
        temp_elem = soup.select_one('.wea_weather em')
        if temp_elem:
            weather_data["current_temp"] = temp_elem.text.strip() + "°"

        condition_img = soup.select_one('.wea_weather span img')
        if condition_img:
            weather_data["current_condition"] = condition_img.get('alt', '').strip()

        humidity_elem = soup.select_one('.wea_about span')
        if humidity_elem:
            weather_data["humidity"] = humidity_elem.text.strip()

        wind_elem = soup.select_one('.wea_about em')
        if wind_elem:
            weather_data["wind"] = wind_elem.text.strip()

        # 2. 获取3月29日预报（从15天预报页面）
        forecast_29 = None
        forecast15_url = urls.get("forecast15", urls) if isinstance(urls, dict) else urls

        try:
            response_15 = requests.get(forecast15_url, headers=headers, timeout=10, allow_redirects=True)
            response_15.encoding = 'utf-8'
            soup_15 = BeautifulSoup(response_15.text, 'html.parser')

            # 从15天预报区域(detail_future_grid)查找
            future_div = soup_15.find('div', class_='detail_future_grid')
            if future_div:
                # 每一天在一个li标签中
                forecast_items = future_div.find_all('li')
                for item in forecast_items:
                    # 获取所有week类的span，其中最后一个通常是日期(格式如: 03/29)
                    date_spans = item.find_all('span', class_='week')
                    is_target_date = False
                    for date_span in date_spans:
                        date_text = date_span.text.strip()
                        if f'03/{TARGET_DAY:02d}' in date_text or f'3/{TARGET_DAY}' in date_text or f'{TARGET_DAY}日' in date_text:
                            is_target_date = True
                            break

                    if is_target_date:
                        forecast = {
                            "date": f"3月{TARGET_DAY}日",
                            "condition": "",
                            "temp": "",
                            "wind": ""
                        }

                        # 获取天气状况 - 取第一个wea（白天的天气）
                        wea_spans = item.find_all('span', class_='wea')
                        if wea_spans:
                            forecast["condition"] = wea_spans[0].text.strip()

                        # 获取温度
                        tree_div = item.find('div', class_='tree')
                        if tree_div:
                            high_temp = tree_div.find('b')
                            low_temp = tree_div.find('strong')
                            if high_temp and low_temp:
                                forecast["temp"] = f"{low_temp.text.strip()} ~ {high_temp.text.strip()}"
                            elif high_temp:
                                forecast["temp"] = high_temp.text.strip()

                        forecast_29 = forecast
                        break

        except Exception as e:
            print(f"获取15天预报失败: {e}")

        weather_data["forecast_29"] = forecast_29

        return weather_data

    except Exception as e:
        return {
            "city": city_name,
            "error": str(e),
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }


def format_weather_message(results):
    """格式化天气信息为推送消息"""
    now = datetime.now().strftime("%m月%d日 %H:%M")

    message = f"🏃 半马天气播报 - {now}\n"
    message += "=" * 30 + "\n\n"

    for result in results:
        city = result["city"]
        message += f"📍 {city}\n"

        if "error" in result:
            message += f"  ⚠️ 获取失败: {result['error']}\n\n"
            continue

        # 3月29日预报（只显示预报天气）
        forecast = result.get("forecast_29")
        if forecast:
            message += f"  🌤️ 天气: {forecast.get('condition', 'N/A')}\n"
            message += f"  🌡️ 温度: {forecast.get('temp', 'N/A')}\n"

            # 跑步建议
            condition = forecast.get('condition', '')
            if any(word in condition for word in ['晴', '多云', '阴']):
                message += f"  ✅ 跑步建议: 适宜跑步\n"
            elif any(word in condition for word in ['小雨', '阵雨']):
                message += f"  ⚠️ 跑步建议: 注意防滑，备好雨具\n"
            elif any(word in condition for word in ['中雨', '大雨', '暴雨', '雷']):
                message += f"  ❌ 跑步建议: 天气不佳，关注赛事通知\n"
            else:
                message += f"  ⚡ 跑步建议: 请关注天气变化\n"
        else:
            message += f"  ⚠️ 暂未获取到3月29日预报\n"

        message += "\n" + "-" * 25 + "\n\n"

    message += "💪 祝比赛顺利，PB达成！"
    return message


def push_serverchan(message):
    """使用Server酱推送（微信）"""
    key = PUSH_CONFIG.get("serverchan_key")
    if not key:
        print("未配置 Server酱 Key")
        return False

    import time
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    for attempt in range(3):  # 重试3次
        try:
            url = f"https://sctapi.ftqq.com/{key}.send"
            data = {
                "title": "半马天气播报",
                "desp": message.replace("\n", "\n\n")
            }
            response = requests.post(
                url,
                data=data,
                timeout=30,
                verify=False,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            if response.status_code == 200:
                print("Server酱推送成功")
                return True
            else:
                print(f"Server酱推送失败 (状态码: {response.status_code})")
        except Exception as e:
            print(f"Server酱推送失败 (尝试 {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(2)
    return False


def save_to_file(message):
    """保存到本地文件"""
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    filename = os.path.join(log_dir, f"weather_log_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*50}\n")
        f.write(message)
        f.write(f"\n{'='*50}\n")
    return filename


def main():
    """主函数"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始查询天气...")

    # 抓取所有城市天气
    results = []
    for city_name, url in WEATHER_URLS.items():
        print(f"正在查询 {city_name}...")
        data = fetch_weather(city_name, url)
        results.append(data)

    # 格式化消息
    message = format_weather_message(results)
    print("\n" + "="*50)
    print(message)
    print("="*50)

    # 保存到文件
    log_file = save_to_file(message)
    print(f"\n天气信息已保存到: {log_file}")

    # 推送通知
    if PUSH_CONFIG.get("serverchan_key"):
        if push_serverchan(message):
            print("\n推送成功")
        else:
            print("\n推送失败")
    else:
        print("\n提示: 未配置推送方式")

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 查询完成")

    return results


if __name__ == "__main__":
    main()
