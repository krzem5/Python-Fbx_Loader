import json
import os
import struct
import zlib



HEAD_MAGIC=b"Kaydara FBX Binary\x20\x20\x00\x1a\x00"
BLOCK_SENTINEL_LENGTH=13



def _r_arr(dt,i,f):
	ln,e,l=struct.unpack("<III",dt[i:i+12])
	o=dt[i+12:i+l+12]
	if (e==1):
		o=zlib.decompress(o)
	o=list(struct.unpack("<"+f*ln,o))
	return (i+l+12,o)



def parse(dt,i):
	e=struct.unpack("<I",dt[i:i+4])[0]
	if (e==0):
		return (None,{})
	pc=struct.unpack("<I",dt[i+4:i+8])[0]
	ln=struct.unpack("B",dt[i+12:i+13])[0]
	o={"name":str(dt[i+13:i+13+ln],"utf-8")}
	if (pc>0):
		o["data"]=[]
	i+=13+ln
	for _ in range(0,pc):
		if (chr(dt[i])=="Y"):
			o["data"]+=[struct.unpack("<h",dt[i+1:i+3])[0]]
			i+=3
		elif (chr(dt[i])=="C"):
			o["data"]+=[struct.unpack("?",dt[i+1:i+2])[0]]
			i+=2
		elif (chr(dt[i])=="I"):
			o["data"]+=[struct.unpack("<i",dt[i+1:i+5])[0]]
			i+=5
		elif (chr(dt[i])=="F"):
			o["data"]+=[struct.unpack("<f",dt[i+1:i+5])[0]]
			i+=5
		elif (chr(dt[i])=="D"):
			o["data"]+=[struct.unpack("<d",dt[i+1:i+9])[0]]
			i+=9
		elif (chr(dt[i])=="L"):
			o["data"]+=[struct.unpack("<q",dt[i+1:i+9])[0]]
			i+=9
		elif (chr(dt[i])=="R"):
			ln=struct.unpack("<I",dt[i+1:i+5])[0]
			o["data"]+=["".join([f"\\x{hex(e)[2:].rjust(2,'0')}" for e in dt[i+5:i+ln+5]])]
			i+=ln+5
		elif (chr(dt[i])=="S"):
			ln=struct.unpack("<I",dt[i+1:i+5])[0]
			o["data"]+=[str(dt[i+5:i+ln+5],"utf-8").replace("\x00\x01","::")]
			i+=ln+5
		elif (chr(dt[i])=="f"):
			i,el=_r_arr(dt,i+1,"f")
			o["data"]+=[el]
		elif (chr(dt[i])=="i"):
			i,el=_r_arr(dt,i+1,"i")
			o["data"]+=[el]
		elif (chr(dt[i])=="d"):
			i,el=_r_arr(dt,i+1,"d")
			o["data"]+=[el]
		elif (chr(dt[i])=="l"):
			i,el=_r_arr(dt,i+1,"q")
			o["data"]+=[el]
		elif (chr(dt[i])=="b"):
			i,el=_r_arr(dt,i+1,"b")
			o["data"]+=[el]
		elif (chr(dt[i])=="c"):
			i,el=_r_arr(dt,i+1,"c")
			o["data"]+=[el]
		else:
			raise RuntimeError("AAA")
	if (i<e):
		o["children"]=[]
		while (i<e-BLOCK_SENTINEL_LENGTH):
			i,el=parse(dt,i)
			if (i==None):
				raise RuntimeError("AAA")
			o["children"]+=[el]
		if (dt[i:i+BLOCK_SENTINEL_LENGTH]!=b"\x00"*BLOCK_SENTINEL_LENGTH):
			raise RuntimeError("AAA")
		i+=BLOCK_SENTINEL_LENGTH
	if (i!=e):
		print(i,e)
		raise IOError("Scope Not Reached!")
	return (i,o)



for k in os.listdir("."):
	if (k[-4:]==".fbx"):
		with open(k,"rb") as f:
			dt=f.read()
		if (dt[:len(HEAD_MAGIC)]!=HEAD_MAGIC):
			continue
		with open(f"{k[:-4]}.json","w") as f:
			i=len(HEAD_MAGIC)+4
			l=[]
			while (i<len(dt)):
				i,e=parse(dt,i)
				if (i==None):
					break
				l+=[e]
			f.write(json.dumps(l,indent=4,sort_keys=False).replace("    ","\t"))
