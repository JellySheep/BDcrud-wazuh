def payload(name="TestBD"):
    return {"name": name, "description": "from_unit_test", "price": 222.0, "qty": 333, "category": "lab"}

def test_create_product(client):
    r = client.post("/products", json=payload("A"))
    assert r.status_code == 201
    assert r.json()["name"] == "A"

def test_list_products(client):
    client.post("/products", json=payload("B"))
    r = client.get("/products")
    assert r.status_code == 200
    assert any(x.get("name") == "B" for x in r.json())

def test_patch_product(client):
    pid = client.post("/products", json=payload("C")).json()["id"]
    r = client.patch(f"/products/{pid}", json={"qty": 999})
    assert r.status_code == 200
    assert r.json()["qty"] == 999

def test_delete_product(client):
    pid = client.post("/products", json=payload("D")).json()["id"]
    r = client.delete(f"/products/{pid}")
    assert r.status_code == 204
    r2 = client.get(f"/products/{pid}")
    assert r2.status_code == 404
