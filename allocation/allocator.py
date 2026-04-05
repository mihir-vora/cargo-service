from __future__ import annotations

from dataclasses import dataclass


class AllocationError(Exception):
    pass


@dataclass(frozen=True)
class CargoSpec:
    cargo_id: str
    volume: int


@dataclass(frozen=True)
class TankSpec:
    tank_id: str
    capacity: int


def parse_cargos(raw: list) -> list[CargoSpec]:
    out: list[CargoSpec] = []
    seen: set[str] = set()
    for row in raw:
        try:
            cid = str(row["id"]).strip()
            vol = int(row["volume"])
        except (KeyError, TypeError, ValueError) as e:
            raise AllocationError("each cargo needs string id and integer volume") from e
        if not cid:
            raise AllocationError("cargo id cannot be empty")
        if vol < 0:
            raise AllocationError("cargo volume cannot be negative")
        if cid in seen:
            raise AllocationError(f"duplicate cargo id: {cid}")
        seen.add(cid)
        out.append(CargoSpec(cid, vol))
    return out


def parse_tanks(raw: list) -> list[TankSpec]:
    out: list[TankSpec] = []
    seen: set[str] = set()
    for row in raw:
        try:
            tid = str(row["id"]).strip()
            cap = int(row["capacity"])
        except (KeyError, TypeError, ValueError) as e:
            raise AllocationError("each tank needs string id and integer capacity") from e
        if not tid:
            raise AllocationError("tank id cannot be empty")
        if cap < 0:
            raise AllocationError("tank capacity cannot be negative")
        if tid in seen:
            raise AllocationError(f"duplicate tank id: {tid}")
        seen.add(tid)
        out.append(TankSpec(tid, cap))
    return out


def allocate(cargos: list[CargoSpec], tanks: list[TankSpec]) -> dict:
    # One tank = one cargo id for its lifetime; space left empty stays unused for others.
    remaining = {c.cargo_id: c.volume for c in cargos}
    unused = {t.tank_id: t.capacity for t in tanks}
    assignments: list[dict] = []

    while unused and any(v > 0 for v in remaining.values()):
        best_tank = None
        best_cargo = None
        best_delta = -1
        best_waste = None

        for tank_id, cap in unused.items():
            if cap <= 0:
                continue
            for cargo_id, need in remaining.items():
                if need <= 0:
                    continue
                take = need if need < cap else cap
                waste = cap - take
                if take > best_delta:
                    best_delta = take
                    best_waste = waste
                    best_tank = tank_id
                    best_cargo = cargo_id
                elif take == best_delta and best_waste is not None and waste < best_waste:
                    best_waste = waste
                    best_tank = tank_id
                    best_cargo = cargo_id

        if best_delta <= 0 or best_tank is None or best_cargo is None:
            break

        cap = unused.pop(best_tank)
        need = remaining[best_cargo]
        take = need if need < cap else cap
        remaining[best_cargo] = need - take
        assignments.append(
            {
                "tank_id": best_tank,
                "cargo_id": best_cargo,
                "loaded_volume": take,
            }
        )

    total = sum(a["loaded_volume"] for a in assignments)
    return {
        "assignments": assignments,
        "total_loaded_volume": total,
        "cargo_remaining": {k: v for k, v in remaining.items() if v > 0},
    }
