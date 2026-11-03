import sys;sys.path.insert(0,'/home/anmire/ai/mosaic')
from mosaic import assets as A
T="full body character concept art, standing straight in a T-pose with both arms held straight out horizontally to the sides, palms down, legs slightly apart, feet flat, front view, symmetrical, whole body visible head to toe, centered, plain light gray studio background, soft even lighting, stylized realistic 3D game character, clean readable shapes, highly detailed"
C={"holo":"an adult woman in her mid twenties with a mature face, heart-shaped face with high cheekbones, hazel eyes, long wavy golden honey blonde hair in two high twin tails tied with black ties, side-swept bangs, smoky winged eyeliner, black choker with a small silver plate, silver chain necklace, fitted black tank top, wide grey studded belt with a square silver buckle, red tartan plaid pleated knee-length skirt, black fingerless leather gloves, black knee socks with two white stripes, black lace-up platform combat boots",
"engineer":"a tall adult man in his early thirties, square jawline, well-groomed short dark beard, swept-back dark brown hair, black rectangular glasses, athletic build, fitted charcoal grey hoodie with the sleeves pushed up to the forearms, dark blue slim jeans, white and grey sneakers"}
for k,d in C.items():
    for s in (sys.argv[1:] or ['7']):
        neg=A.concept_negative(d,'humanoid',True).replace(', female, woman, breasts, feminine face','' if k=='holo' else ', female, woman, breasts, feminine face')+', A-pose, arms down, arms at sides, child, teen, young girl, minor, cropped, cut off feet'
        print(A.concept_image(f"{T}, {d}",f"{k}_{s}.png",'humanoid',int(s),None,neg),flush=True)
