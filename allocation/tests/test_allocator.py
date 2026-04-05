from django.test import SimpleTestCase

from allocation.allocator import (
    AllocationError,
    CargoSpec,
    TankSpec,
    allocate,
    parse_cargos,
    parse_tanks,
)


class ParseTests(SimpleTestCase):
    def test_rejects_duplicate_cargo_ids(self):
        with self.assertRaises(AllocationError):
            parse_cargos(
                [
                    {"id": "C1", "volume": 10},
                    {"id": "C1", "volume": 5},
                ]
            )

    def test_rejects_negative_volume(self):
        with self.assertRaises(AllocationError):
            parse_cargos([{"id": "C1", "volume": -1}])

    def test_rejects_empty_cargo_id(self):
        with self.assertRaises(AllocationError):
            parse_cargos([{"id": "   ", "volume": 1}])

    def test_rejects_malformed_cargo_row(self):
        with self.assertRaises(AllocationError):
            parse_cargos([{"id": "C1"}])

    def test_rejects_duplicate_tank_ids(self):
        with self.assertRaises(AllocationError):
            parse_tanks(
                [
                    {"id": "T1", "capacity": 10},
                    {"id": "T1", "capacity": 5},
                ]
            )

    def test_rejects_negative_tank_capacity(self):
        with self.assertRaises(AllocationError):
            parse_tanks([{"id": "T1", "capacity": -1}])

    def test_rejects_empty_tank_id(self):
        with self.assertRaises(AllocationError):
            parse_tanks([{"id": "", "capacity": 10}])


class AllocateTests(SimpleTestCase):
    def test_splits_one_cargo_across_tanks(self):
        cargos = [CargoSpec("C1", 100)]
        tanks = [
            TankSpec("T1", 40),
            TankSpec("T2", 70),
        ]
        out = allocate(cargos, tanks)
        self.assertEqual(out["total_loaded_volume"], 100)
        by_tank = {a["tank_id"]: a for a in out["assignments"]}
        self.assertEqual(by_tank["T1"]["cargo_id"], "C1")
        self.assertEqual(by_tank["T2"]["cargo_id"], "C1")

    def test_prefers_larger_fit_when_one_tank(self):
        cargos = [CargoSpec("C1", 10), CargoSpec("C2", 100)]
        tanks = [TankSpec("T1", 1000)]
        out = allocate(cargos, tanks)
        self.assertEqual(out["total_loaded_volume"], 100)
        self.assertEqual(len(out["assignments"]), 1)
        self.assertEqual(out["assignments"][0]["cargo_id"], "C2")

    def test_each_tank_row_is_one_cargo_only(self):
        cargos = [CargoSpec("A", 30), CargoSpec("B", 30)]
        tanks = [TankSpec("t1", 20), TankSpec("t2", 20), TankSpec("t3", 50)]
        out = allocate(cargos, tanks)
        cargo_per_tank = {a["tank_id"]: a["cargo_id"] for a in out["assignments"]}
        self.assertEqual(len(cargo_per_tank), len(out["assignments"]))

    def test_empty_inputs(self):
        self.assertEqual(
            allocate([], [])["total_loaded_volume"],
            0,
        )

    def test_all_cargo_volumes_zero(self):
        out = allocate(
            [CargoSpec("C1", 0), CargoSpec("C2", 0)],
            [TankSpec("T1", 100)],
        )
        self.assertEqual(out["total_loaded_volume"], 0)
        self.assertEqual(out["assignments"], [])
        self.assertEqual(out["cargo_remaining"], {})

    def test_all_tank_capacities_zero(self):
        out = allocate(
            [CargoSpec("C1", 50)],
            [TankSpec("T1", 0), TankSpec("T2", 0)],
        )
        self.assertEqual(out["total_loaded_volume"], 0)
        self.assertEqual(out["assignments"], [])
        self.assertEqual(out["cargo_remaining"], {"C1": 50})

    def test_cargo_remaining_when_capacities_too_small(self):
        out = allocate(
            [CargoSpec("C1", 100)],
            [TankSpec("T1", 30)],
        )
        self.assertEqual(out["total_loaded_volume"], 30)
        self.assertEqual(out["cargo_remaining"], {"C1": 70})

    def test_pdf_sample_cargo_volumes_with_symmetric_tanks(self):
        cargos = [
            CargoSpec("C1", 1234),
            CargoSpec("C2", 4352),
            CargoSpec("C3", 3321),
            CargoSpec("C4", 2456),
            CargoSpec("C5", 5123),
            CargoSpec("C6", 1879),
            CargoSpec("C7", 4987),
            CargoSpec("C8", 2050),
            CargoSpec("C9", 3678),
            CargoSpec("C10", 5432),
        ]
        tanks = [
            TankSpec("T1", 1234),
            TankSpec("T2", 4352),
            TankSpec("T3", 3321),
            TankSpec("T4", 2456),
            TankSpec("T5", 5123),
            TankSpec("T6", 1879),
            TankSpec("T7", 4987),
            TankSpec("T8", 2050),
            TankSpec("T9", 3678),
            TankSpec("T10", 5432),
        ]
        out = allocate(cargos, tanks)
        total_cargo = sum(c.volume for c in cargos)
        self.assertEqual(out["total_loaded_volume"], total_cargo)
        self.assertEqual(out["cargo_remaining"], {})
