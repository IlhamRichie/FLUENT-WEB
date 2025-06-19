from datetime import datetime, timezone, timedelta

# Tentukan zona waktu WIB (UTC+7)
WIB = timezone(timedelta(hours=7))

def format_to_wib(value):
    """
    Filter untuk mengubah UTC datetime ke format tanggal dan waktu WIB.
    Contoh: 19 Juni 2025, 22:30
    """
    if not isinstance(value, datetime):
        return value
    
    # Jika datetime 'naive', asumsikan itu UTC
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
        
    wib_time = value.astimezone(WIB)
    return wib_time.strftime('%d %b %Y, %H:%M')

def format_to_wib_timesince(value):
    """
    Filter untuk mengubah UTC datetime menjadi format 'time since' (misal: 5 menit yang lalu)
    """
    if not isinstance(value, datetime):
        return value

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    now_utc = datetime.now(timezone.utc)
    diff = now_utc - value

    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "baru saja"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} menit yang lalu"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} jam yang lalu"
    elif seconds < 2592000: # sekitar 30 hari
        days = int(seconds / 86400)
        return f"{days} hari yang lalu"
    else:
        # Jika lebih dari sebulan, tampilkan tanggal saja
        wib_time = value.astimezone(WIB)
        return wib_time.strftime('%d %b %Y')
