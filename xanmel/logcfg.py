import logging.config

logging.config.dictConfig(
    {
        'version': 1,
        'formatters': {
            'simple': {
                'format': '%(asctime)s [%(levelname)s] %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'simple'
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console']
        }
    })
