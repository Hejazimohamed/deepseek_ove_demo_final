import datetime

def log_user_event(event):
    """تسجيل حدث للمستخدم مع الطابع الزمني"""
    with open("user_events.log", "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().isoformat()
        f.write(f"{timestamp}: {event}\n")