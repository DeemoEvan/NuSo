import asyncio
import edge_tts

# 在這裡輸入你想說的英文台詞
TEXT = "You're so low on IQ points that you can't even remember what I said. You really are as dumb as the rest of your family, aren't you? Ha! Your family is so pathetic"
# Aria 是最推薦的英文女聲，質感非常像你之前的 temp_base 檔案
VOICE = "en-US-AriaNeural"
OUTPUT_FILE = "neuro_input_en.mp3"

async def amain() -> None:
    communicate = edge_tts.Communicate(TEXT, VOICE)
    await communicate.save(OUTPUT_FILE)

if __name__ == "__main__":
    asyncio.run(amain())