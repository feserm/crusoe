import click
import os
import logging

from icecream import ic
from commands.create import create

@click.group()
@click.option('-c', '--config', default='config.yaml', help='Path to the configuration file')
@click.option('-v', '--verbose', count=True, help='Verbosity level')
@click.pass_context
def cli(ctx, config, verbose):
    if verbose == 1:
        logging.basicConfig(level=logging.INFO)
    ctx.ensure_object(dict)
    ctx.obj['config'] = os.path.expanduser(config)

@cli.command()
@click.pass_context
def start(ctx):
    """
    Start the infrastructure
    """
    create(ctx.obj['config'])

@cli.command()
def terminate():
    """
    Tear down the infrastructure
    """
    click.echo('Not implemted yet!')
    
@cli.command()
def check():
    """
    Validate the configuration file
    """
    click.echo('Not implemted yet!')

if __name__ == '__main__':
    cli()