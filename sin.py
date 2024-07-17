import asyncio

d = {}


class TestDel:

    def __init__(self, name):
        self.name = name

    async def loop(self):
        while True:
            await asyncio.sleep(1)
            print('Hello from courutine', self.name)

    async def clean_up(self):
        print('clean up called')
        del d[self.name]
        loop = asyncio.get_running_loop()
        print('recreated task after deleting')
        loop.create_task(self.loop())


d['1'] = TestDel('1')
d['2'] = TestDel('2')


async def main():
    #loop = asyncio.get_running_loop()
    loop.create_task(d['1'].loop())
    loop.create_task(d['2'].loop())
    await asyncio.sleep(5)
    loop.create_task(d['1'].clean_up())
    await asyncio.sleep(2)
    try:
        print(d['1'])
    except:
        print('item deleted')
    loop.run_forever()


loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
