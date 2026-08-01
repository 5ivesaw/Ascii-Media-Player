ASCII Media Player for macOS

Open "ASCII Media Player.command" to start the terminal application, or run ./ascii-media-player from Terminal.

The builds are not Apple-notarized. If Gatekeeper blocks the downloaded archive, open Terminal in this folder and run:

  xattr -dr com.apple.quarantine .

Then open the .command file again. FFmpeg is optional and can be installed with Homebrew: brew install ffmpeg
