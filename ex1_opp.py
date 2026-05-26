
import hid

def main():
    devices = hid.enumerate()

    if not devices:
        print("HID-устройства не найдены.")
        return

    print("Все HID-устройства:")
    for d in devices:
        mfr = d["manufacturer_string"] or ""
        prod = d["product_string"] or ""
        print(
            f"{d['vendor_id']:04X}:{d['product_id']:04X} | "
            f"{mfr} | {prod} | "
            f"usage_page=0x{d['usage_page']:04X} usage=0x{d['usage']:04X}"
        )

    print("\nУстройства, похожие на HyperX:")
    found = False
    for d in devices:
        mfr = (d["manufacturer_string"] or "").lower()
        prod = (d["product_string"] or "").lower()
        if "hyperx" in mfr or "hyperx" in prod:
            found = True
            print(
                f"{d['vendor_id']:04X}:{d['product_id']:04X} | "
                f"{d['manufacturer_string']} | {d['product_string']}"
            )

    if not found:
        print("HyperX-устройство не найдено в списке HID.")

if __name__ == "__main__":
    main()