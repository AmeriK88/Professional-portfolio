try:
    import pymysql  # noqa
    pymysql.install_as_MySQLdb()
except Exception:
    pass
