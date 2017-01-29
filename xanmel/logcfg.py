def logging_config(level):
    return {
        'version': 1,
        'propagate': True,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '%(asctime)s [%(levelname)s] %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': level,
                'formatter': 'simple'
            }
        },
        # 'loggers': {
        #     'asyncio': {
        #         'level': 'DEBUG',
        #         'handlers': ['console']
        #     },
        # },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console']
        }
    }
