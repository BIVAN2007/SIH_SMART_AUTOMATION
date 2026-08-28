"""
test_ws_client.py
Quick manual test for the live-stream WebSocket endpoint. Run the server
first (uvicorn app.main:app --reload), then in another terminal:

    python test_ws_client.py village_road

Prints each telemetry tick as it arrives -- this is the same message shape
your React dashboard will receive and render.
"""
import asyncio
import json
import sys

import websockets

SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "village_road"
URL = f"ws://localhost:8000/ws/live/{SCENARIO}"


async def main():
    async with websockets.connect(URL) as ws:
        print(f"Connected to {URL}")
        async for message in ws:
            telem = json.loads(message)
            print(f"t={telem['t']:5.1f}s  mode={telem['mode']:16s}  "
                  f"pos={telem['ego_pos']}  speed={telem['ego_speed_kmh']:5.1f}km/h  "
                  f"clearance={telem['min_clearance_m']:5.2f}m  "
                  f"replan={telem['replan_latency_ms']:5.2f}ms")
            if telem["done"]:
                print("Run finished. collision =", telem["collision"])
                break


if __name__ == "__main__":
    asyncio.run(main())
