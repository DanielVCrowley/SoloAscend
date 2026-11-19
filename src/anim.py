"""Анимации: появление, пульсация, упругие эффекты, плавное кольцо прогресса."""
import asyncio
import time

import flet as ft


class AnimMixin:
    def reveal(self, control, animate):
        if not animate:
            return control
        wrapper = ft.Container(
            content=control,
            opacity=0,
            offset=ft.Offset(0, 0.08),
            scale=0.97,
            animate_opacity=ft.Animation(450, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(600, ft.AnimationCurve.EASE_OUT_CUBIC),
            animate_scale=ft.Animation(600, ft.AnimationCurve.EASE_OUT_CUBIC),
        )
        self.pending.append(wrapper)
        return wrapper

    async def play_reveal(self, items, generation, delay=0.11):
        await asyncio.sleep(0.06)
        for wrapper in items:
            if generation != self.generation:
                return
            wrapper.opacity = 1
            wrapper.offset = ft.Offset(0, 0)
            wrapper.scale = 1
            self.page.update()
            await asyncio.sleep(delay)

    def anim(self, control, delay, **final):
        """Запланировать смену свойств контрола после отрисовки — сработает его implicit-анимация."""
        self.anims.append((delay, control, final))
        return control

    def pop_in(self, control, delay=0.15, start=0.4, ms=850, expand=None):
        """Упругое появление: контрол «выпрыгивает» из маленького размера."""
        wrapper = ft.Container(
            content=control,
            expand=expand,
            scale=start,
            opacity=0,
            animate_scale=ft.Animation(ms, ft.AnimationCurve.ELASTIC_OUT),
            animate_opacity=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
        )
        return self.anim(wrapper, delay, scale=1, opacity=1)

    def slide_in(self, control, delay=0.1, dx=0.0, dy=0.25, ms=550):
        wrapper = ft.Container(
            content=control,
            opacity=0,
            offset=ft.Offset(dx, dy),
            animate_opacity=ft.Animation(ms, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(ms, ft.AnimationCurve.EASE_OUT_BACK),
        )
        return self.anim(wrapper, delay, opacity=1, offset=ft.Offset(0, 0))

    def pulse(self, control, amount=1.06):
        """Мягкое «дыхание» — контрол слегка увеличивается и уменьшается по такту тикера."""
        wrapper = ft.Container(
            content=control,
            animate_scale=ft.Animation(700, ft.AnimationCurve.EASE_IN_OUT),
        )
        self.live.setdefault("pulses", []).append((wrapper, amount))
        return wrapper

    async def play_anims(self, items, generation=None):
        started = time.monotonic()
        for delay, control, final in sorted(items, key=lambda x: x[0]):
            wait = delay - (time.monotonic() - started)
            if wait > 0:
                await asyncio.sleep(wait)
            if generation is not None and generation != self.generation:
                return
            for attr, value in final.items():
                setattr(control, attr, value)
            try:
                self.page.update()
            except Exception:
                return

    async def tween_ring(self, progress, label, counter, start, end, finished, total, generation):
        steps = 24
        for i in range(1, steps + 1):
            await asyncio.sleep(0.025)
            if generation != self.generation:
                return
            t = 1 - (1 - i / steps) ** 3
            value = start + (end - start) * t
            progress.value = value
            label.value = f"{round(value * 100)}%"
            self.page.update()
        counter.value = f"{finished}/{total}"
        self.page.update()

    def tick_pulses(self):
        now = time.monotonic()
        if now - self.pulse_clock < 0.75:
            return False
        self.pulse_clock = now
        self.pulse_on = not self.pulse_on
        pulses = self.live.get("pulses", [])
        for wrapper, amount in pulses:
            wrapper.scale = amount if self.pulse_on else 1
        return bool(pulses)

    async def vibrate(self, times=2):
        if self.haptics:
            try:
                for i in range(times):
                    if i:
                        await asyncio.sleep(0.15)
                    await self.haptics.heavy_impact()
            except Exception:
                pass
