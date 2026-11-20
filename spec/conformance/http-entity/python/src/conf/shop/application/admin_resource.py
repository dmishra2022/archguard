from conf.shop.http.routing import admin_router


@admin_router.get('/')
def status() -> str:
    return 'ok'
