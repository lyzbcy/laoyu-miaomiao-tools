# 云转写的免费用量准入

默认复用可用本地稿件、边界或已安装模型。需要云端字级稿时才考虑Scribe；有免费额度也不等于获准上传。当前包只提供纯离线测量、算术预检与手动余额快照契约，**没有联网余额适配器、上传器、付费路径或凭据配置功能**。

## 调用前把成本说清

1. 明确拟上传的文件/音轨、接收方ElevenLabs、用途、API渠道、模型ID与选项。先导出实际待上传音频并用ffprobe测总时长，不能拿成片时长代替输入长度；多音轨、重复尝试、分批和并发均计入。隐私素材先确认允许传输的范围，不能用云转写绕过本地隐私处理。
2. 从已授权可访问的当前API账户用量/计费页或受支持只读接口取得**剩余免费**额度、单位、模型/渠道适用范围、重置时间、来源与查询时刻。不新增API key，不让用户把密钥贴聊天；未来如需密钥，仅走受支持的安全流程，不写日志、skill或版本库。没有授权访问、无法确认余额/重置或单位时填unknown；套餐标称额度和网页UI免费分钟不算API账户余额。
3. 默认报告预计输入分钟/小时及明确假设；只有有来源、有效期、同模型/渠道/选项的换算依据才能换算credits。费率仅作带核查日期的参考，附来源和选项范围；额外功能可能另计费，不能把参考单价自动当最终账单。预检默认逐文件向上取整到秒、10%时长预留，这是可配置估算假设，不是ElevenLabs官方计费粒度。未验证计费方式就说明估算可能偏差。
4. 扣除未反映在余额快照中的在途预留，再看是否足够；不确定已提交是否成功的请求先查结果/账单并保持预留，不盲重传。共享额度的并发任务须用单一负责人或外部原子台账协调；本脚本不实现原子扣减，运行后重新核对余额/预留，不能拿同一快照并行放行。
5. 给出下述确认信息，取得用户对这批文件和本次计划的明确批准后才能真正上传。文件、模型、选项、重试次数、余额快照或预留变化就重新计算；超出原批准范围需重确认。余额不足或未知保持阻塞，提供本地转写备选，不自动付费、充值或开按量计费。本次授权更新skill本身不等于任何上传批准。
6. 缓存成功转写结果：音频哈希、音轨、提供方、渠道、模型和完整选项构成key，另核验结果文件哈希。缓存失效才重算；不能把失败/半成品或另一模型的稿件当命中。实际上传后将消耗、账单/余额来源与重置时间写项目，不能只记估算。

确认文案应包括：“拟上传哪些音频至ElevenLabs用于转写；模型/渠道/选项；输入长度、重试及预留；预计免费消耗；当前可核实免费剩余、来源与查询时间；预计使用后剩余与重置时间；不足/未知时如何处理；是否产生付费；是否批准本次上传。”未知值直写unknown，不用套餐数字填空。脚本生成的计划指纹可绑定这次确认，但指纹和布尔值本身不能替代用户原话证据。

## 可运行的离线预检

```powershell
python scripts/transcription_preflight.py measure voice.wav --output work/measured-v1.json
# 将测得inputs合入项目request，并填写已核实的余额快照；不要写密钥。
python scripts/transcription_preflight.py plan work/request-v1.json --output work/preflight-v1.json
```

先建项目work目录。`scripts/fixtures/transcription-request.json`是可复制配置格式；其中路径、零哈希和时长是合成fixture，不能当真实测量。`plan`会再次测量实际文件并核对哈希/时长；失败就停止，输出拒绝覆盖旧文件。所有命令只在本地执行，不读取环境密钥、不发网络请求。即使状态为`approved_preflight_only`，`upload_allowed`和`paid_allowed`始终为false；未来上传适配器须独立实现、测试并再次核对实时余额和批准。

`balance`填写provider/model/channel、remaining、unit（seconds/minutes/hours/credits）、scope（同一个免费额度池的本地标识）、source、带时区queried_at/reset_at；默认快照15分钟有效，过期、未来时间或已过重置点均unknown。credits另填conversion中的credits_per_second、同模型/渠道、source、verified_at和options_digest（规范JSON选项的SHA256）。没有可信换算留空，不猜系数。

`reservations`填scope、unit、amount、status（reserved/uncertain/submitted）和included_in_snapshot；只有明确尚未计入快照才再扣，状态不明或单位不匹配阻塞。`cache`填key/status/result_path/result_sha256；`approval`填explicit、plan_digest和用户批准记录reference，不能伪造。`price_reference`可选，需provider/model/channel、usd_per_hour、source、as_of和options_digest；输出gross_reference_usd只是含预留的名义总价参考，未扣免费额度，不是付费授权或已发生账单。使用非标准选项时自行核查完整费用。

本地Whisper/对齐的输出需按实际接口转换为源时间字表，再进入EDL。0.10.0新增`local_transcribe.py`实际调用既有faster-whisper，输出兼容源字表，命令与验证范围见[integration](integration.md)；机器边界仍需校正。这不是video-use的Whisper后端，Scribe上传/联网余额适配仍未实现。真人耳听与误识别校对继续独立。

## 带日期的官方参考

2026-10-23核查：[API语音转文字页面](https://join.elevenlabs.io/api/speech-to-text)列每月10,000免费credits及Scribe v1/v2参考价$0.22/小时；[API定价页](https://elevenlabs.io/pricing/api)列Scribe v2免费档约4小时30分钟。两者是套餐说明，不是当前账户余额；v2的标称时间不能套给video-use默认的v1，也不能套网页UI。费率、可用模型、选项和额度以后可能变化，实际调用前重查。[按量付费说明](https://elevenlabs.io/docs/overview/administration/pay-as-you-go)仅用于理解账单边界，不因预检不足自动启用。
