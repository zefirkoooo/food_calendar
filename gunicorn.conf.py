import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1

wsgi_app = "food_calendar.wsgi:application"

worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

accesslog = "-"
errorlog = "-"
loglevel = "info"

limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190 