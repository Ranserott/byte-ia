# Personalización del Orb

OpenJarvis no incluye un componente de orb predefinido en la app principal,
pero `frontend/src/components/OrbCustom.tsx` trae un orb animado en canvas
listo para usar cuando construyas una vista de voz / TUI.

## Uso

```tsx
import { OrbCustom } from "@/components/OrbCustom";

<OrbCustom state="listening" audioLevel={0.5} />
```

`state` acepta `"idle" | "listening" | "thinking" | "speaking"` y cambia la
paleta de color. `audioLevel` (0..1) hace que el orb pulse con la amplitud
del mic o del TTS.

## Customizar colores

La paleta por defecto es:

```ts
const ORB_DEFAULT_COLORS = {
  idle: "#f54a00",       // naranja terracota
  listening: "#06b6d4",   // cyan
  thinking: "#eab308",    // amarillo
  speaking: "#10b981",    // verde
};
```

Podés sobreescribir la paleta de dos formas:

**Por instancia** (la más simple):

```tsx
<OrbCustom
  state="listening"
  size={300}
  colors={{ listening: "#ff00aa", speaking: "#00ff66" }}
/>
```

**Globalmente**: editá la constante `ORB_DEFAULT_COLORS` exportada desde
`OrbCustom.tsx`.

## Customizar tamaño

El `size` base se multiplica por 1.2x para dejar espacio al glow.

```tsx
<OrbCustom state="idle" size={400} />   // más grande
<OrbCustom state="idle" size={120} />   // mini-orb para listas
```

## Accesibilidad

El contenedor expone `role="img"` con un `aria-label` que anuncia el estado
actual (`"Assistant orb — listening"`), y el canvas lleva `data-state`
para test selectors.
