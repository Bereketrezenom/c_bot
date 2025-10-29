"""
Simple standalone bot runner.
"""
import logging


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)


def main() -> None:
    from bot.bot_app.app import run as run_app
    run_app()


if __name__ == '__main__':
    main()


