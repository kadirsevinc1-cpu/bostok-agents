from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message


SYSTEM = """Sen Bostok.dev web ajansının Yönetici agent'ısın.

Bostok.dev hakkında: Profesyonel web tasarım ve geliştirme ajansı. https://bostok.dev

Görevin:
1. Müşteriden gelen talepleri analiz et
2. Analist'e brief çıkarması için gönder
3. Teklif agent'ından fiyat al
4. İçerik, Tasarım, Developer, QA, Deploy agent'larını sırayla yönet
5. Kalite kontrolü yap
6. Demo hazır olunca kullanıcıya bildir
7. Onay alınca yayına al

Kurallar:
- Bütçe aşımında sistemi durdur
- Her adımı hafızaya kaydet
- Müşteriye Türkçe ve profesyonel ilet
- Kararlarını kısa gerekçeyle açıkla"""


class ManagerAgent(BaseAgent):
    name = AgentName.MANAGER
    system_prompt = SYSTEM
    max_tokens = 1500

    def __init__(self):
        super().__init__()
        # Mevcut proje bilgisi — Developer sonucundan gelir, Deploy'a iletilir
        self._current_site_dir: str = ""
        self._current_project_name: str = ""

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._process(msg)

    async def _process(self, msg: Message):
        from loguru import logger

        logger.info(f"Yonetici mesaj aldi: {msg.sender.value} -> {msg.content[:80]}")
        self.save_observation(f"Mesaj: [{msg.sender.value}] {msg.content[:200]}", importance=7.0)

        if msg.type == MessageType.CLIENT_REQUEST:
            await self.send(
                AgentName.ANALYST, MessageType.TASK,
                msg.content,
                {"source": msg.sender.value},
            )
            await self.send(
                AgentName.SYSTEM, MessageType.USER_NOTIFY,
                "Talebiniz alındı. Analist brief hazırlıyor, ardından teklif ve içerik oluşturulacak.",
            )

        elif msg.type == MessageType.RESULT:
            result = msg.content

            if msg.sender == AgentName.MARKETING:
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                f"Pazarlama Raporu:\n{result}")

            elif msg.sender == AgentName.ANALYST:
                project_name = msg.metadata.get("project_name", "")
                if project_name:
                    self._current_project_name = project_name
                meta = {"project_name": self._current_project_name}

                # Konsey toplantısı — 3 uzman paralel oy kullanır (~500 token)
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                "Konsey toplantısı başladı, brief değerlendiriliyor...")
                from core.council import hold_meeting
                decision = await hold_meeting(result)
                self.save_observation(f"Konsey: {decision.report()[:200]}", importance=9.0)
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY, decision.report())

                if not decision.approved:
                    return  # 2/3 RET — pipeline durduruldu

                await self.send(AgentName.QUOTE, MessageType.TASK, result, meta)
                await self.send(AgentName.CONTENT, MessageType.TASK, result, meta)

            elif msg.sender == AgentName.QUOTE:
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                f"Teklif hazir:\n{result}")

            elif msg.sender == AgentName.CONTENT:
                await self.send(AgentName.DESIGNER, MessageType.TASK, result,
                                {"project_name": self._current_project_name})

            elif msg.sender == AgentName.DESIGNER:
                await self.send(AgentName.DEVELOPER, MessageType.TASK, result,
                                {"project_name": self._current_project_name})

            elif msg.sender == AgentName.DEVELOPER:
                # Site dizinini sakla — QA'dan sonra Deploy'a göndereceğiz
                file_path = msg.metadata.get("file_path", "")
                self._current_project_name = msg.metadata.get("project_name", "site")
                from pathlib import Path
                if file_path:
                    self._current_site_dir = str(Path(file_path).parent)
                await self.send(AgentName.QA, MessageType.TASK, result,
                                {"file_path": file_path,
                                 "site_dir": self._current_site_dir,
                                 "project_name": self._current_project_name})

            elif msg.sender == AgentName.QA:
                has_critical = msg.metadata.get("has_critical_errors", False)
                site_dir = msg.metadata.get("site_dir", self._current_site_dir)
                project_name = msg.metadata.get("project_name", self._current_project_name)

                if has_critical:
                    await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                    f"QA kritik hata buldu, deploy durduruldu:\n\n{result[:500]}")
                else:
                    await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                    f"QA tamamlandi, site yukleniyor...\n\n{result[:300]}")
                    await self.send(
                        AgentName.DEPLOY, MessageType.TASK,
                        result,
                        {"site_dir": site_dir, "project_name": project_name},
                    )

            elif msg.sender == AgentName.DEPLOY:
                # Deploy tamamlandı → kullanıcıya demo linki sun
                url = msg.metadata.get("url", "")
                local = msg.metadata.get("local_path", "")

                if url:
                    notify = (
                        f"Site demo hazir!\n\n"
                        f"Demo linki: {url}\n\n"
                        f"Yayinda kalmasi icin onay verin."
                    )
                else:
                    notify = (
                        f"Netlify deploy yapilamadi.\n"
                        f"Site yerel olarak hazir: {local}\n\n"
                        f"Netlify token'i .env'e ekleyerek otomatik deploy yapilabilir."
                    )
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY, notify,
                                {"requires_approval": bool(url)})

        elif msg.type == MessageType.STATUS and msg.metadata.get("user_note"):
            note_type = msg.metadata.get("note_type", "not")
            note = msg.content
            self.save_observation(f"Kullanici {note_type}: {note}", importance=9.0)
            response = await self.ask(
                f"Kullanicidan '{note_type}' notu geldi: {note}\n"
                "Bu notu mevcut is akisina nasil yansitacagini acikla ve gerekli adimi at."
            )
            await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY, response)

        elif msg.type == MessageType.APPROVAL:
            await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                            "Onay alindi! Site yayinda.")
            self.save_observation("Site yayina alindi", importance=9.0)

        elif msg.type == MessageType.BUDGET_ALERT:
            await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                            f"Butce Uyarisi: {msg.content}")
