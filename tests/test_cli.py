import json

from deberka_jordan.cli import main


def test_plan(tmp_path, capsys):
    f = tmp_path / "state.csv"
    f.write_text("consumer,current,target\nvm1,2000,2600\nvm2,3000,2500\nvm3,1500,1530\n")
    assert main(["plan", str(f), "--pool", "100", "--deadband", "64"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["donors"] == {"vm2": 500.0}
    assert out["recipients"] == {"vm1": 600.0}
    assert out["skipped"] == {"vm3": 30.0}
    assert out["min_pool_two_phase"] >= 0


def test_net(tmp_path, capsys):
    f = tmp_path / "log.csv"
    f.write_text("cycle,donor,recipient,amount_mib\n1,a,b,100\n1,b,c,100\n2,a,c,64\n")
    out_csv = tmp_path / "net.csv"
    assert main(["net", str(f), "--out", str(out_csv)]) == 0
    s = json.loads(capsys.readouterr().out)
    assert s["cycles"] == 2
    assert s["overall_gain"] == 1 - (200 + 128) / (400 + 128)
    assert out_csv.read_text().startswith("cycle,")


def test_deadband(tmp_path, capsys):
    f = tmp_path / "trace.csv"
    rows = ["t_s,vm1,vm2"] + [
        f"{k},{1000 + (k % 7) * 30},{2000 - (k % 5) * 50}" for k in range(300)
    ]
    f.write_text("\n".join(rows) + "\n")
    out_csv = tmp_path / "db.csv"
    assert main(["deadband", str(f), "--h", "0,64,128", "--out", str(out_csv)]) == 0
    text = capsys.readouterr().out
    assert "chosen h" in text
    assert len(out_csv.read_text().splitlines()) == 4
