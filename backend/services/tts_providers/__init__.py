"""
TTS 提供方插件目录：各厂商/本地实现放在此包内，由 tts_service 按配置调度。

新增提供方（尽量少改核心逻辑）：
1. 在本包新增模块，实现 synthesize(text, cfg_block) -> Optional[bytes]
2. 在 tts_service._synthesize_with_provider() 中增加分支，或调用 register_tts_provider()
3. 在 tts_config.yaml 中增加配置块，并设置 provider
"""
