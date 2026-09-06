import pygame
import pygame._sdl2.audio as sdl2_audio
import time

def neuro_relay_play(filename):
    pygame.mixer.init()
    
    # --- 自動尋找虛擬電纜 ---
    devices = sdl2_audio.get_audio_device_names(False)
    target_device = None
    
    print("🔎 正在掃描音訊設備...")
    for name in devices:
        print(f"找到設備: {name}")
        if "CABLE Input" in name:
            target_device = name
            break

    if not target_device:
        print("❌ 找不到 VB-Cable。請確認已安裝並重啟電腦。")
        return

    # --- 使用虛擬設備重啟 Mixer ---
    pygame.mixer.quit()
    pygame.mixer.init(devicename=target_device)
    
    print(f"🚀 正在將聲音餵入變聲器 (透過 {target_device})...")
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    
    pygame.mixer.quit()
    print("✅ 播放完成")

if __name__ == "__main__":
    # 先隨便拿一個 mp3 或 wav 測試
    neuro_relay_play("neuro_input_en.mp3")