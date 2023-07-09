import asyncio
from src.cls_bot import Husky
import json


async def main():
    husky = Husky()
    env = open("env.json", "r")
    token = json.load(env)["discord"]["token"]

    await husky.login(token)
    await husky.connect()


if __name__ == "__main__":
    asyncio.run(main())
