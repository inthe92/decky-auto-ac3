"""Automatic AC-3 HDMI routing for Decky on SteamOS."""

import asyncio
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

import decky


PROFILE_SET = "hdmi-ac3.conf"
AC3_PROFILE_PREFIX = "output:hdmi-ac3-surround"
CUSTOM_PROFILE_NAME = "9999-decky-dolby-digital.conf"
# On this Deck/dock this is the known-good fallback route: it is the profile
# previously shown in the UI as "HDMI 5", which returns audio to the console.
FALLBACK_CONSOLE_PROFILE = "output:hdmi-ac3-surround-extra3"
CONFIG_NAME = "99-decky-dolby-digital.conf"
POLL_SECONDS = 3

WIREPLUMBER_CONFIG = '''# Managed by Decky Dolby Digital. Remove this file to disable it.
monitor.alsa.rules = [
  {
    # Do not apply the HDMI profile to the Deck's ACP audio coprocessor:
    # that device owns the built-in speakers and headphone jack.
    matches = [ {
      device.name = "~alsa_card.pci-.*"
      device.description = "~.*(Radeon|HDMI|High Definition Audio).*"
    } ]
    actions = {
      update-props = {
        api.acp.disable-pro-audio = true
        device.profile-set = "hdmi-ac3.conf"
        device.routes.default-sink-volume = 1.0
      }
    }
  },
  {
    matches = [ { node.name = "~alsa_output.pci-.*hdmi.*" } ]
    actions = { update-props = { session.suspend-timeout-seconds = 3600 } }
  },
  {
    matches = [ { node.name = "~alsa_output.pci-.*hdmi.*" alsa.name = "~a52.*" } ]
    actions = { update-props = { api.alsa.start-delay = 1536 } }
  }
]
'''


class Plugin:
    def _config_path(self) -> Path:
        return Path(decky.DECKY_USER_HOME) / ".config/wireplumber/wireplumber.conf.d" / CONFIG_NAME

    def _user_ac3_profile_path(self) -> Path:
        return Path(decky.DECKY_USER_HOME) / ".config/alsa-card-profile/mixer/profile-sets" / CUSTOM_PROFILE_NAME

    def _ensure_local_alsa_card_profile_tree(self) -> tuple[bool, str]:
        """Copy the whole system alsa-card-profile tree (paths, profile-sets,
        etc.) into the user's own config, exactly like the manual fix: cp -r
        /usr/share/alsa-card-profile -> ~/.config/alsa-card-profile. A local
        copy under the user's home survives OS updates/resets and guarantees
        every profile-set file is present even if the running system image
        ships an incomplete set for this particular unit."""
        target_root = Path(decky.DECKY_USER_HOME) / ".config/alsa-card-profile"
        if target_root.exists():
            return False, ""
        source_root = Path("/usr/share/alsa-card-profile")
        if not source_root.exists():
            return False, "No se encontró /usr/share/alsa-card-profile en el sistema."
        try:
            shutil.copytree(source_root, target_root)
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI as-is
            return False, f"No se pudo copiar alsa-card-profile a .config: {exc}"
        return True, ""

    def _ac3_profile_available(self) -> bool:
        system_profile = Path("/usr/share/alsa-card-profile/mixer/profile-sets", PROFILE_SET)
        return system_profile.exists() or self._user_ac3_profile_path().exists()

    def _ensure_ac3_profile(self) -> tuple[bool, str]:
        """Mirror the manual fix step by step, every time, regardless of
        what's already present:
          1. cp -r /usr/share/alsa-card-profile -> ~/.config/alsa-card-profile
             (skipped if the destination already exists).
          2. Copy mixer/profile-sets/hdmi-ac3.conf to 9999-custom.conf in that
             same (now-local) folder, so alsa-card-profile always finds our
             AC-3 mappings under the user's own config, independent of which
             profile-set the running system happens to assign to this card.
        If the system doesn't ship hdmi-ac3.conf at all, fall back to the
        template bundled with the plugin. Returns (changed_anything, error).
        """
        _, error = self._ensure_local_alsa_card_profile_tree()
        if error:
            return False, error

        profile_sets_dir = Path(decky.DECKY_USER_HOME) / ".config/alsa-card-profile/mixer/profile-sets"
        custom_profile = profile_sets_dir / CUSTOM_PROFILE_NAME
        if custom_profile.exists():
            return False, ""

        profile_sets_dir.mkdir(parents=True, exist_ok=True)
        system_hdmi_ac3 = Path("/usr/share/alsa-card-profile/mixer/profile-sets", PROFILE_SET)
        source_text = None
        if system_hdmi_ac3.exists():
            source_text = system_hdmi_ac3.read_text(encoding="utf-8")
        else:
            template = Path(decky.DECKY_PLUGIN_DIR, "defaults", "hdmi-ac3-profile.conf")
            if template.exists():
                source_text = template.read_text(encoding="utf-8")
        if source_text is None:
            return False, "No se encontró ni el perfil AC-3 del sistema ni la plantilla incluida en el plugin."
        custom_profile.write_text(source_text, encoding="utf-8")
        return True, ""

    async def _run(self, *command: str) -> tuple[int, str, str]:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"},
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout.decode().strip(), stderr.decode().strip()

    async def _pactl_json(self, *args: str) -> Any:
        code, stdout, stderr = await self._run("pactl", "--format=json", *args)
        if code:
            raise RuntimeError(stderr or "No se pudo consultar PipeWire.")
        return json.loads(stdout)

    @staticmethod
    def _profiles(card: dict[str, Any]) -> list[str]:
        profiles = card.get("profiles", [])
        if isinstance(profiles, list):
            return [item.get("name", "") for item in profiles if isinstance(item, dict)]
        if isinstance(profiles, dict):
            return list(profiles)
        return []

    @staticmethod
    def _active_profile(card: dict[str, Any]) -> str:
        active = card.get("active_profile")
        return active.get("name", "") if isinstance(active, dict) else (active or "")

    @staticmethod
    def _profile_for_port(port_name: str) -> str | None:
        match = re.fullmatch(r"hdmi-output-(\d+)", port_name)
        if not match:
            return None
        port_number = int(match.group(1))
        return AC3_PROFILE_PREFIX if port_number == 0 else f"{AC3_PROFILE_PREFIX}-extra{port_number}"

    @staticmethod
    def _profile_for_alsa_hdmi_device(device_number: int) -> str | None:
        # The number after the dot in /proc/asound/cardX/eld#C.N is the HDMI
        # pin/converter index (0, 1, 2, 3…), which lines up 1:1 with the
        # "hdmi-output-N" PipeWire port suffix, not with an ALSA PCM device
        # number. Reuse the same numbering as _profile_for_port.
        if device_number < 0:
            return None
        return AC3_PROFILE_PREFIX if device_number == 0 else f"{AC3_PROFILE_PREFIX}-extra{device_number}"

    async def _audio_state(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return await self._pactl_json("list", "cards"), await self._pactl_json("list", "sinks")

    def _connected_hdmi_target(self, cards: list[dict[str, Any]]) -> tuple[str, str, str] | None:
        """Return card, AC-3 profile and PipeWire port for the connected HDMI."""
        for card in cards:
            profiles = self._profiles(card)
            for port in card.get("ports", []):
                if not isinstance(port, dict) or port.get("availability") != "available":
                    continue
                port_name = port.get("name", "")
                profile = self._profile_for_port(port_name)
                if profile and profile in profiles:
                    return card.get("name", ""), profile, port_name

        # Some docks/TVs report every PipeWire HDMI port as "unknown". ALSA's
        # ELD files still reveal the physically connected HDMI monitor.
        for eld_path in Path("/proc/asound").glob("card*/eld#*.*"):
            try:
                eld = eld_path.read_text(encoding="utf-8", errors="ignore")
                if not re.search(r"^monitor_present\s+1$", eld, re.MULTILINE):
                    continue
                if not re.search(r"^eld_valid\s+1$", eld, re.MULTILINE):
                    continue
                match = re.fullmatch(r"card(\d+)/eld#\d+\.(\d+)", str(eld_path.relative_to("/proc/asound")))
                if not match:
                    continue
                alsa_card, alsa_device = match.groups()
                profile = self._profile_for_alsa_hdmi_device(int(alsa_device))
                if not profile:
                    continue
                for card in cards:
                    properties = card.get("properties", {})
                    same_card = str(properties.get("alsa.card", "")) == alsa_card
                    is_hdmi_card = "high definition audio" in str(properties.get("device.description", "")).lower()
                    if (same_card or is_hdmi_card) and profile in self._profiles(card):
                        return card.get("name", ""), profile, f"ELD HDMI device {alsa_device}"
            except OSError:
                continue
        return None

    async def _set_profile(self, card_name: str, profile: str) -> tuple[bool, str]:
        code, _, error = await self._run("pactl", "set-card-profile", card_name, profile)
        if code:
            return False, error or "No se pudo cambiar el perfil de audio."
        await asyncio.sleep(1)
        _, sinks = await self._audio_state()
        # PipeWire's sink "device.profile.name" property omits the
        # "output:"/"input:" scope prefix that pactl uses for card profiles,
        # e.g. card profile "output:hdmi-ac3-surround-extra2" shows up on the
        # sink as "hdmi-ac3-surround-extra2". Compare on the unscoped name.
        target_profile_name = profile.split(":", 1)[-1]
        for sink in sinks:
            properties = sink.get("properties", {})
            if properties.get("device.profile.name") == target_profile_name:
                await self._run("pactl", "set-default-sink", sink.get("name", ""))
                break
        return True, ""

    async def _switch_to_internal_speakers(self) -> bool:
        _, sinks = await self._audio_state()
        # Deck's built-in speakers expose an analog PipeWire sink. Avoid HDMI,
        # Bluetooth and virtual sinks when choosing the fallback.
        for sink in sinks:
            name = sink.get("name", "")
            lower = name.lower()
            properties = sink.get("properties", {})
            description = " ".join(str(value) for value in (
                sink.get("description", ""),
                properties.get("device.description", ""),
                properties.get("node.description", ""),
                properties.get("node.nick", ""),
            )).lower()
            if "audio coprocessor speaker" in description:
                code, _, _ = await self._run("pactl", "set-default-sink", name)
                return code == 0
            if "analog" in lower and "hdmi" not in lower and "bluez" not in lower:
                code, _, _ = await self._run("pactl", "set-default-sink", name)
                return code == 0

        # Some SteamOS/dock combinations do not expose the Deck's fallback as
        # an `analog` sink. Reuse the profile that is known to restore audio on
        # this hardware instead of leaving the user without sound.
        cards, _ = await self._audio_state()
        for card in cards:
            if FALLBACK_CONSOLE_PROFILE in self._profiles(card):
                ok, _ = await self._set_profile(card.get("name", ""), FALLBACK_CONSOLE_PROFILE)
                return ok
        return False

    async def _apply_automatic_route(self) -> dict[str, Any]:
        cards, _ = await self._audio_state()
        target = self._connected_hdmi_target(cards)
        if target is None:
            switched = await self._switch_to_internal_speakers()
            self.current_route = "internal" if switched else "none"
            return {"ok": switched, "route": self.current_route, "message": "No hay HDMI activo; se ha restaurado el audio de la consola."}

        card_name, profile, port_name = target
        if self.current_route == profile:
            return {"ok": True, "route": profile, "port": port_name, "message": "Dolby Digital ya está activo."}
        ok, error = await self._set_profile(card_name, profile)
        if ok:
            self.current_route = profile
            return {"ok": True, "route": profile, "port": port_name, "message": f"Dolby Digital activado automáticamente en {port_name}."}
        return {"ok": False, "route": self.current_route, "message": error}

    async def _watch_audio_routes(self):
        while True:
            try:
                if self._config_path().exists():
                    await self._apply_automatic_route()
                else:
                    self.current_route = "disabled"
            except asyncio.CancelledError:
                raise
            except Exception as error:
                decky.logger.warning("Automatic audio routing failed: %s", error)
            await asyncio.sleep(POLL_SECONDS)

    async def get_status(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "enabled": self._config_path().exists(),
            "profile_set_present": self._ac3_profile_available(),
            "connected_port": "",
            "current_route": getattr(self, "current_route", "disabled"),
            "default_sink": "",
            "error": "",
        }
        try:
            cards, _ = await self._audio_state()
            target = self._connected_hdmi_target(cards)
            if target:
                result["connected_port"] = target[2]
            _, result["default_sink"], _ = await self._run("pactl", "get-default-sink")
        except Exception as error:
            result["error"] = str(error)
        return result

    async def enable_automatic(self) -> dict[str, Any]:
        if not Path("/usr/lib/alsa-lib/libasound_module_pcm_a52.so").exists():
            return {"ok": False, "message": "No se encontró el codificador ALSA a52 de SteamOS."}
        installed, error = self._ensure_ac3_profile()
        if error:
            return {"ok": False, "message": error}
        if not self._ac3_profile_available():
            return {"ok": False, "message": "No se encontró el perfil HDMI AC-3 de SteamOS."}
        config = self._config_path()
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(WIREPLUMBER_CONFIG, encoding="utf-8")
        if installed:
            # A fresh profile-set file needs PipeWire itself restarted (not
            # just WirePlumber) to be picked up by alsa-card-profile.
            await self._run("systemctl", "--user", "restart", "pipewire")
            await asyncio.sleep(1)
        await self._run("systemctl", "--user", "restart", "wireplumber")
        await asyncio.sleep(2)
        self.current_route = ""
        outcome = await self._apply_automatic_route()
        outcome["status"] = await self.get_status()
        if installed:
            note = "Se instaló también el perfil de audio AC-3 5.1 en tu configuración de usuario."
            outcome["message"] = f"{outcome.get('message', '')} {note}".strip()
        return outcome

    async def switch_to_internal(self) -> dict[str, Any]:
        # This is a manual escape hatch. Automatic routing resumes when HDMI is
        # disconnected or when the automatic mode is re-enabled.
        ok = await self._switch_to_internal_speakers()
        self.current_route = "internal" if ok else self.current_route
        return {"ok": ok, "message": "Audio de consola seleccionado." if ok else "No se encontró una salida de audio de consola.", "status": await self.get_status()}

    async def _main(self):
        self.current_route = "disabled"
        self.watch_task = asyncio.create_task(self._watch_audio_routes())
        decky.logger.info("Decky Dolby Digital automatic routing loaded")

    async def _unload(self):
        self.watch_task.cancel()
        decky.logger.info("Decky Dolby Digital unloaded")

    async def _uninstall(self):
        self._config_path().unlink(missing_ok=True)
        await self._run("systemctl", "--user", "restart", "wireplumber")
