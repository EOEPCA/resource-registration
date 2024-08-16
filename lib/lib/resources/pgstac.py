from pypgstac.pypgstac import PgstacCLI


def import_stac_items(input, dsn, debug=False, method="insert_ignore"):
    """
    Description...

    Parameters:
        input: x
        dsn: x
        debug: x
        method: x
    """
    cli = PgstacCLI(dsn=dsn, debug=debug)
    cli.load(table="items", file=input, method=method)
