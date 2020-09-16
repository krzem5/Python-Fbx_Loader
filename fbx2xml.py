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
	o=",".join([str(e) for e in list(struct.unpack("<"+f*ln,o))])
	return (i+l+12,o)



def parse(dt,i,f,il):
	e=struct.unpack("<I",dt[i:i+4])[0]
	if (e==0):
		return None
	pc=struct.unpack("<I",dt[i+4:i+8])[0]
	ln=struct.unpack("B",dt[i+12:i+13])[0]
	t=str(dt[i+13:i+13+ln],"utf-8")
	i+=13+ln
	at=""
	ad=[None for _ in range(0,pc)]
	for j in range(0,pc):
		at+=chr(dt[i])
		i+=1
		if (at[-1]=="Y"):
			ad[j]=struct.unpack("<h",dt[i:i+2])[0]
			i+=2
		elif (at[-1]=="C"):
			ad[j]=struct.unpack("?",dt[i:i+1])[0]
			i+=1
		elif (at[-1]=="I"):
			ad[j]=struct.unpack("<i",dt[i:i+4])[0]
			i+=4
		elif (at[-1]=="F"):
			ad[j]=struct.unpack("<f",dt[i:i+4])[0]
			i+=4
		elif (at[-1]=="D"):
			ad[j]=struct.unpack("<d",dt[i:i+8])[0]
			i+=8
		elif (at[-1]=="L"):
			ad[j]=struct.unpack("<q",dt[i:i+8])[0]
			i+=8
		elif (at[-1]=="R"):
			ln=struct.unpack("<I",dt[i:i+4])[0]
			ad[j]="".join([f"\\x{hex(e)[2:].rjust(2,'0')}" for e in dt[i+4:i+4+ln]])
			i+=ln+4
		elif (at[-1]=="S"):
			ln=struct.unpack("<I",dt[i:i+4])[0]
			ad[j]=str(dt[i+4:i+4+ln],"utf-8").replace("\x00\x01","::")
			i+=ln+4
		elif (at[-1]=="f"):
			i,ad[j]=_r_arr(dt,i,"f")
		elif (at[-1]=="i"):
			i,ad[j]=_r_arr(dt,i,"i")
		elif (at[-1]=="d"):
			i,ad[j]=_r_arr(dt,i,"d")
		elif (at[-1]=="l"):
			i,ad[j]=_r_arr(dt,i,"q")
		elif (at[-1]=="b"):
			i,ad[j]=_r_arr(dt,i,"b")
		elif (at[-1]=="c"):
			i,ad[j]=_r_arr(dt,i,"c")
		else:
			raise RuntimeError("AAA")
	f.write("\t"*il+f"<{t}")
	if (pc>0):
		f.write(f" type{('' if pc==1 else 's')}=\"{at}\"")
		if (pc==1):
			f.write(f" value=\"{ad[0]}\"")
		else:
			for j in range(0,pc):
				f.write(f" v{j}=\"{ad[j]}\"")
	if (i<e):
		f.write(">\n")
		while (i<e-BLOCK_SENTINEL_LENGTH):
			i=parse(dt,i,f,il+1)
			if (i==None):
				raise RuntimeError("AAA")
		f.write("\t"*il+f"</{t}>\n")
		if (dt[i:i+BLOCK_SENTINEL_LENGTH]!=b"\x00"*BLOCK_SENTINEL_LENGTH):
			raise RuntimeError("AAA")
		i+=BLOCK_SENTINEL_LENGTH
	else:
		f.write("/>\n")
	if (i!=e):
		print(i,e)
		raise IOError("Scope Not Reached!")
	return i



for k in os.listdir("."):
	if (k[-4:]==".fbx"):
		with open(k,"rb") as f:
			dt=f.read()
		if (dt[:len(HEAD_MAGIC)]!=HEAD_MAGIC):
			continue
		with open(f"{k[:-4]}.xml","w") as f:
			f.write(f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n<fbx version=\"{struct.unpack(b'<I',dt[len(HEAD_MAGIC):len(HEAD_MAGIC)+4])[0]}\">\n")
			i=len(HEAD_MAGIC)+4
			while (i<len(dt)):
				i=parse(dt,i,f,1)
				if (i==None):
					break
			f.write("</fbx>\n")
