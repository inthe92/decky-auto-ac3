import { ButtonItem, PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";
import { callable, definePlugin, toaster } from "@decky/api";
import { useEffect, useState } from "react";
import { FaVolumeUp } from "react-icons/fa";

type Status = { enabled: boolean; profile_set_present: boolean; connected_port: string; current_route: string; default_sink: string; error: string };
type Action = { ok: boolean; message: string; status?: Status };

const getStatus = callable<[], Status>("get_status");
const enableAutomatic = callable<[], Action>("enable_automatic");
const switchToInternal = callable<[], Action>("switch_to_internal");

function Content() {
  const [status, setStatus] = useState<Status>();
  const [working, setWorking] = useState(false);
  const refresh = async () => setStatus(await getStatus());
  useEffect(() => { refresh(); }, []);

  const apply = async (action: () => Promise<Action>) => {
    setWorking(true);
    try {
      const result = await action();
      toaster.toast({ title: result.ok ? "Dolby Digital" : "Audio", body: result.message });
      setStatus(result.status ?? await getStatus());
    } finally { setWorking(false); }
  };

  const route = status?.connected_port
    ? `HDMI detectado: ${status.connected_port}`
    : "Sin HDMI detectado: se restaurará el audio de la consola.";

  return <PanelSection title="Dolby Digital 5.1">
    <PanelSectionRow><div>{status?.enabled ? "Cambio automático activado" : "Cambio automático desactivado"}</div></PanelSectionRow>
    <PanelSectionRow><div>{route}</div></PanelSectionRow>
    <PanelSectionRow>
      <ButtonItem layout="below" disabled={working || !status?.profile_set_present} onClick={() => apply(enableAutomatic)}>
        Activar cambio automático HDMI
      </ButtonItem>
    </PanelSectionRow>
    <PanelSectionRow>
      <ButtonItem layout="below" disabled={working} onClick={() => apply(switchToInternal)}>
        Usar audio de consola ahora
      </ButtonItem>
    </PanelSectionRow>
    {status?.error && <PanelSectionRow><div>{status.error}</div></PanelSectionRow>}
  </PanelSection>;
}

export default definePlugin(() => ({
  name: "Dolby Digital",
  titleView: <div className={staticClasses.Title}>Dolby Digital 5.1</div>,
  content: <Content />,
  icon: <FaVolumeUp />,
}));
