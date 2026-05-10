import os

print("Rebuilding images.c with custom GBA art...")

out = open("images.c", "w")
out.write('#include "gui.h"\n\n')

theme_dir = "../../themes/default"
files =[f for f in os.listdir(theme_dir) if f.endswith(".png") or f.endswith(".json")]
names =[]

for f in files:
    name = f.replace(".", "_").replace("-", "_")
    names.append(name)
    with open(os.path.join(theme_dir, f), "rb") as img_file:
        data = img_file.read()
    
    out.write(f'static const binfile_t {name} = {{"{f}", {len(data)}, {{\n')
    
    # Write image bytes into C array format
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        out.write("    " + ", ".join([str(b) for b in chunk]) + ",\n")
        
    out.write("}};\n\n")

# Write the final index array that the launcher reads
out.write("const binfile_t *builtin_images[ ] = {\n")
for name in names:
    out.write(f"    &{name},\n")
out.write("    NULL\n};\n")
out.close()
print("Success! images.c has been updated.")