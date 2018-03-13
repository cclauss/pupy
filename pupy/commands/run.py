# -*- encoding: utf-8 -*-

# TODO: Fix stream/interaction

from pupylib.PupyModule import PupyArgumentParser
from pupylib.PupyOutput import Error, Success
from pupylib.PupyJob import PupyJob
from argparse import REMAINDER

usage = 'Run a module on one or multiple clients'
parser = PupyArgumentParser(prog='run', description=usage)

parser.add_argument('module', metavar='<module>', help="module")
parser.add_argument('-1', '--once', default=False, action='store_true', help='Unload new deps after usage')
parser.add_argument('-o', '--output', help='save command output to file.'
                        '%%t - timestamp, %%h - host, %%m - mac, '
                        '%%c - client shortname, %%M - module name, '
                        '%%p - platform, %%u - user, %%a - ip address')
parser.add_argument(
    '-f', '--filter', metavar='<client filter>',
    help='filter to a subset of all clients. All fields available in the "info" module can be used. '
    'example: run get_info -f \'platform:win release:7 os_arch:64\'')
parser.add_argument('-b', '--background', action='store_true', help='run in background')
parser.add_argument('arguments', nargs=REMAINDER, default='', metavar='<arguments>', help='module arguments')

def do(server, handler, config, modargs):
    pj = None
    args = modargs.arguments
    clients_filter = modargs.filter or handler.default_filter

    try:
        module = server.get_module(
            server.get_module_name_from_category(modargs.module))

    except Exception as e:
        handler.display(Error(e, modargs.module))
        return

    if not module:
        handler.display(Error('Unknown module', modargs.module))
        return

    clients = server.get_clients(clients_filter)
    if not clients:
        if not server.clients:
            handler.display(Error('No clients currently connected'))
        else:
            handler.display(Error('No clients match this search!'))
        return

    modjobs = [
        job for job in server.jobs.itervalues()
        if job.module.get_name() == module.get_name() and
        any(instance in clients for instance in job.clients)
    ]

    pj = None
    interactive = False
    unique = False

    if module.daemon and module.unique_instance and modjobs:
        pj = modjobs[0]
        unique = True
    else:
        pj = PupyJob(
            server,
            module, '{} {}'.format(modargs.module, ' '.join(args)))

        add_job = True

        ios = handler.acquire_io(
            module.io, len(clients), modargs.background or module.daemon)

        for io, client in zip(ios, clients):
            io.set_title(str(client))
            instance = module(client, pj, io, log=modargs.output)
            pj.add_module(instance)

    try:
        pj.start(args, once=modargs.once)

    except Exception as e:
        handler.display(Error(e))
        pj.stop()

    handler.process(
        pj,
        background=modargs.background,
        daemon=module.daemon,
        unique=unique
    )
