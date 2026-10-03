"""Deterministic positive cases and adversarial controls; standard library only."""
from copy import deepcopy
from fractions import Fraction as F
import json
from math import comb
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

import checker as c

ROOT = Path(__file__).resolve().parent


def certificate(power, degree=None, name="reference"):
    degree = len(power)-1 if degree is None else degree
    # Independent forward conversion, not the checker's expansion algorithm.
    bern = [sum((power[i]*F(comb(k,i), comb(degree,i))
                 for i in range(min(k+1, len(power)))), F(0)) for k in range(degree+1)]
    return {"id": name, "domain": ["0","1"], "power": list(map(str,power)),
            "bernstein": list(map(str,bern)), "lower": str(min(bern)), "upper": str(max(bern))}


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.doc = c.read(ROOT / "qutrit_denominators.json")

    def test_40_existing_polynomials(self):
        self.assertEqual(len(c.verify(self.doc)["cases"]), 40)

    def test_fixture_binding(self):
        bindings = json.loads((ROOT / "source_bindings.json").read_text())
        self.assertEqual(len(bindings["intervals"]), 40)
        for i,(case,row) in enumerate(zip(self.doc["cases"],bindings["intervals"])):
            self.assertEqual(case["id"], f"D{i}")
            self.assertEqual(case["power"], row["power"])
            self.assertEqual(case["bernstein"], row["bernstein"])
            self.assertEqual(case["lower"], "1")
            self.assertEqual(case["upper"], str(max(map(F,row["bernstein"]))))

    def test_400_forward_conversion_and_point_checks(self):
        rng = random.Random(2601002)
        for trial in range(400):
            degree = trial % 17
            power = [F(rng.randrange(-20,21),rng.randrange(1,30)) for _ in range(degree+1)]
            case = certificate(power)
            c.verify_case(case)
            lo,hi = F(case["lower"]), F(case["upper"])
            for x in (F(0),F(1,7),F(1,2),F(6,7),F(1)):
                val = sum((p*x**i for i,p in enumerate(power)),F(0))
                self.assertLessEqual(lo,val)
                self.assertLessEqual(val,hi)

    def test_degree_elevation(self):
        for degree in range(2,17):
            c.verify_case(certificate([F(1),F(-4),F(4)],degree))

    def test_constant_zero_and_signs(self):
        for value in (F(0),F(-2),F(3,7)):
            c.verify_case(certificate([value]))

    def test_240_semantic_mutations(self):
        for original in self.doc["cases"]:
            mutations = []
            for field in ("power", "bernstein"):
                q = deepcopy(original); q[field][0] = str(F(q[field][0])+1); mutations.append(q)
            q = deepcopy(original); q["lower"] = str(max(map(F,q["bernstein"]))+1); mutations.append(q)
            q = deepcopy(original); q["upper"] = str(min(map(F,q["bernstein"]))-1); mutations.append(q)
            q = deepcopy(original); q["domain"] = ["0","2"]; mutations.append(q)
            q = deepcopy(original); q["bernstein"].reverse(); mutations.append(q)
            for q in mutations:
                with self.assertRaises(c.Rejected): c.verify_case(q)

    def test_unproved_true_bound_is_rejected(self):
        # (2x-1)^2 >= 0 is true, but this degree-2 Bernstein certificate
        # has middle coefficient -1 and does not establish that lower bound.
        case = certificate([F(1),F(-4),F(4)]); case["lower"]="0"
        with self.assertRaises(c.Rejected): c.verify_case(case)

    def test_duplicate_ids_and_unknown_fields(self):
        doc=deepcopy(self.doc); doc["cases"][1]["id"]=doc["cases"][0]["id"]
        with self.assertRaises(c.Rejected): c.verify(doc)
        doc=deepcopy(self.doc); doc["proof"]=True
        with self.assertRaises(c.Rejected): c.verify(doc)

    def test_empty_oversized_cases_and_degrees(self):
        for count in (0,129):
            doc={"schema":c.SCHEMA,"cases":[self.doc["cases"][0]]*count}
            with self.assertRaises(c.Rejected): c.verify(doc)
        case=deepcopy(self.doc["cases"][0]);case["bernstein"]=["1"]*18
        with self.assertRaises(c.Rejected): c.verify_case(case)

    def test_rational_parser_limits(self):
        for q in ("01", "-0", "2/2", "1/0", "1/-2", "0.5", "1e6", "1 /2", "NaN", "9"*100, True, 1, None):
            with self.assertRaises(c.Rejected): c.rational(q)

    def test_strict_json(self):
        for data in (b'{"a":"x","a":"y"}', b'{"a":NaN}', b'{"a":1}', b'{"a":1.2}', b'\xff', b'{', b' '* (c.MAX_BYTES+1), b'['*2000+b']'*2000):
            with self.assertRaises(c.Rejected): c.loads(data)

    def test_schema_and_field_types(self):
        for key,value in (("id",None),("domain",None),("power",[]),("bernstein",{}),("lower",False),("upper",[])):
            q=deepcopy(self.doc["cases"][0]);q[key]=value
            with self.assertRaises(c.Rejected): c.verify_case(q)
        q=deepcopy(self.doc);q["schema"]="untrusted"
        with self.assertRaises(c.Rejected):c.verify(q)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"case.json"
            for valid in (True,False):
                doc=deepcopy(self.doc)
                if not valid:doc["cases"][0]["power"][0]="0"
                path.write_text(json.dumps(doc),encoding="utf-8")
                run=subprocess.run([sys.executable,"-B",str(ROOT/"checker.py"),str(path)],capture_output=True,text=True,timeout=15)
                self.assertEqual(run.returncode,0 if valid else 1)
                self.assertEqual(json.loads(run.stdout)["status"],"VERIFIED_POLYNOMIAL_ENCLOSURES" if valid else "REJECTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
