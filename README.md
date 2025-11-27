If you have a Huidu HD-WF4 led controller and want to update it from code, without using Huidu SDKs, this project maybe will be useful to you.

We leverage the "Real-time area" functionality of this controller to update the entire screen with an image of our choosing.

This was reverse engineered from captured packets sent from HDSign. Tested on a 160x32 Full Color screen, which can show 8 different colors.

## Implementations

This project includes both C# and Python implementations.

### Python Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the example:
   ```bash
   python huidu_realtime.py
   ```

3. Use in your code:
   ```python
   import asyncio
   import numpy as np
   from huidu_realtime import send_mat, create_text_image

   # Create an image with text
   mat = create_text_image("Hello")

   # Or create your own 160x32 BGR image
   mat = np.zeros((32, 160, 3), dtype=np.uint8)
   mat[:, :, :] = [255, 0, 0]  # Blue

   # Send to controller
   asyncio.run(send_mat(mat, controller_ip="192.168.4.1"))
   ```

### C# Usage

Build and run the solution:
```bash
dotnet run
```

## Protocol Details

- Controller IP: 192.168.4.1 (default)
- Controller Port: 6101
- Server Port: 12345
- Display Size: 160x32 pixels
- Color Format: 8 colors (3-bit RGB, threshold at 170)
