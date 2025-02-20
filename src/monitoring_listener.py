import asyncio
async def handle_client(reader, writer, script_queue):
    task_name = (await reader.read(1024)).decode().strip()
    print(f"Received task: {task_name}")

    # Create an event specific to this task
    task_event = asyncio.Event()

    # Add the task to the queue
    await script_queue.put((task_name, task_event, reader, writer))
    print(f"Task '{task_name}' added to queue")

    # Wait for the task to complete
    await task_event.wait()

    # Notify the client
    writer.write(f"Task '{task_name}' finished\n".encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def process_queue(script_queue, com_port_lock):
    while True:
        task_name, task_event, reader, writer = await script_queue.get()
        print(f"Processing task: {task_name}")

        # Lock the COM port
        async with com_port_lock:
            print("COM port locked")
            writer.write("START\n".encode())
            await writer.drain()

            # Wait for client response
            client_response = await reader.read(1024)
            print(f"Client response: {client_response.decode().strip()}")

        # Mark the task as complete
        script_queue.task_done()
        task_event.set()

async def main():
    # Initialize shared resources in the same loop
    script_queue = asyncio.Queue()
    com_port_lock = asyncio.Lock()

    # Start the task processor
    asyncio.create_task(process_queue(script_queue, com_port_lock))

    # Start the server
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, script_queue),
        "127.0.0.1",
        8888
    )
    print("Server running on 127.0.0.1:8888")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())