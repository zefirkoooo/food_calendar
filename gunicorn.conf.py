import multiprocessing

# Количество воркеров
workers = multiprocessing.cpu_count() * 2 + 1

# Путь к приложению
wsgi_app = "food_calendar.wsgi:application"

# Настройки воркеров
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Настройки логирования
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Настройки безопасности
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190 