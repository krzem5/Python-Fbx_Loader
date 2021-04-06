import math
import os
import panda3d.core
import struct
import zlib



HEAD_MAGIC=b"Kaydara FBX Binary\x20\x20\x00\x1a\x00"
BLOCK_SENTINEL_LENGTH=13
STRIDE=8



def _r_arr(dt,i,f):
	ln,e,l=struct.unpack("<III",dt[i:i+12])
	o=dt[i+12:i+l+12]
	if (e==1):
		o=zlib.decompress(o)
	o=list(struct.unpack(f"<{ln}{f}",o))
	return (i+l+12,o)



def _parse(dt,i):
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
			raise RuntimeError(chr(dt[i]))
	if (i<e):
		o["children"]=[]
		while (i<e-BLOCK_SENTINEL_LENGTH):
			i,el=_parse(dt,i)
			if (i is None):
				raise RuntimeError("AAA")
			o["children"]+=[el]
		if (dt[i:i+BLOCK_SENTINEL_LENGTH]!=b"\x00"*BLOCK_SENTINEL_LENGTH):
			raise RuntimeError("AAA")
		i+=BLOCK_SENTINEL_LENGTH
	if (i!=e):
		print(i,e)
		raise IOError("Scope Not Reached!")
	return (i,o)



def _get_child(o,nm):
	for e in o["children"]:
		if (e["name"]==nm):
			return e
	return None



def _get_prop70(o,nm):
	for e in o["children"]:
		if (e["name"]=="P" and e["data"][0]==nm):
			return e["data"][4:]
	return None



def _get_frame(off,f):
	return math.ceil(((f-off[0])//46186158)/(1000/60))



def _get_refs(cl,ol,id_,k=None):
	if (k==-1):
		return [(e[1],ol[e[0]]) for e in cl[id_] if e[0] in list(ol.keys())]
	for e in cl[id_]:
		if (e[1]==k):
			return ol[e[0]]
	return None



def _name(nm):
	return nm.split(" ")[-1][:-len(nm.split("::")[-1])-2]



def _write_anim(f,off,cl,ol,m):
	p=_get_prop70(_get_child(m,"Properties70"),"Lcl Translation")
	r=_get_prop70(_get_child(m,"Properties70"),"Lcl Rotation")
	l=_get_refs(cl,ol,m["id"],-1)
	dt={"x":[p[0]],"y":[p[1]],"z":[p[2]],"rx":[r[0]],"ry":[r[1]],"rz":[r[2]]}
	fl=0
	c=0
	for et,e in l:
		if (e["type"]=="Model"):
			c+=1
		elif (e["type"]=="AnimationCurveNode"):
			al=_get_refs(cl,ol,e["id"],-1)
			for t,k in al:
				if (len(t)!=3 or t[:2]!="d|" or t[2] not in "xyzXYZ"):
					raise RuntimeError
				kl=_get_child(k,"KeyTime")["data"][0]
				kv=_get_child(k,"KeyValueFloat")["data"][0]
				dt[("" if et=="Lcl Translation" else "r")+t[2].lower()]=([] if kl[0]==0 else [(0,dt[("" if et=="Lcl Translation" else "r")+t[2].lower()])])
				lk=None
				for i,v in enumerate(kl):
					if (lk!=None and _get_frame(off,v)<=lk):
						continue
					if (lk!=None and lk<_get_frame(off,v)-1):
						j=_get_frame(off,kl[i-1])+1
						ln=_get_frame(off,v)-_get_frame(off,kl[i-1])
						while (j!=_get_frame(off,v)):
							dt[("" if et=="Lcl Translation" else "r")+t[2].lower()]+=[kv[i-1]+j/ln*(kv[i]-kv[i-1])]
							j+=1
					dt[("" if et=="Lcl Translation" else "r")+t[2].lower()]+=[kv[i]]
					lk=_get_frame(off,v)
				if (len(kl)>1 and lk!=None and lk<off[1]+1):
					j=lk+1
					ln=off[1]+1-lk
					while (j!=off[1]+1):
						dt[("" if et=="Lcl Translation" else "r")+t[2].lower()]+=[kv[i-1]+j/ln*(kv[i]-kv[i-1])]
						j+=1
				if (len(dt[("" if et=="Lcl Translation" else "r")+t[2].lower()])>1):
					fl|=(1<<(ord(t[2].lower())-120+(0 if et=="Lcl Translation" else 3)))
	nm=_name(m["name"])
	for k in ("rx","ry","rz"):
		dt[k]=[e/180*math.pi for e in dt[k]]
	f.write(struct.pack(f"<B{len(nm[:255])}sBB{sum([len(e) for e in dt.values()])}f",len(nm[:255]),bytes(nm[:255],"utf-8"),fl,c,*dt["x"],*dt["y"],*dt["z"],*dt["rx"],*dt["ry"],*dt["rz"]))
	for et,e in l:
		if (e["type"]=="Model"):
			_write_anim(f,off,cl,ol,e)



def _write_poses(f,cl,ol,pl):
	def _join(l,ch,k):
		if (k in list(ch.keys())):
			if ("children" not in list(l[k].keys())):
				l[k]["children"]=[]
			for e in ch[k]:
				l=_join(l,ch,e)
				l[k]["children"]+=[l[e]]
				del l[e]
		return l
	def _read_mdl(cl,ol,l,ch,nr,k,anr,bi):
		print(" "*bi+f"Reading Model '{k['name']}'...")
		if (_name(k["name"]) not in list(l.keys())):
			l[_name(k["name"])]={}
		l[_name(k["name"])]["dx"],l[_name(k["name"])]["dy"],l[_name(k["name"])]["dz"]=_get_prop70(_get_child(k,"Properties70"),"Lcl Translation")
		l[_name(k["name"])]["name"]=k["name"]
		g=[[],[],[],[],[],[],[]]
		m=None
		if (anr==True):
			nr+=[_name(k["name"])]
		print(" "*bi+"Reading Children...")
		for et,e in _get_refs(cl,ol,k["id"],-1):
			if (e["type"]=="NodeAttribute"):
				print(" "*bi+"Parsing Attributes...")
				l[_name(k["name"])]["len"]=_get_prop70(_get_child(e,"Properties70"),"Size")[0]
			elif (e["type"]=="Model"):
				if (_name(k["name"]) not in list(ch.keys())):
					ch[_name(k["name"])]=[e["name"][:-len(e["name"].split("::")[-1])-2]]
				elif (e["name"][:-len(e["name"].split("::")[-1])-2] not in ch[_name(k["name"])]):
					ch[_name(k["name"])]+=[e["name"][:-len(e["name"].split("::")[-1])-2]]
				l,ch,nr,tg,tm=_read_mdl(cl,ol,l,ch,nr,e,True,bi+2)
				if (tm!=None and m!=None):
					raise RuntimeError("Duplicate Material!")
				print(" "*bi+"Merging Data...")
				if (tm!=None):
					m=tm
				for i,j in enumerate(tg):
					g[i]+=j
			elif (e["type"]=="Geometry"):
				print(" "*bi+"Parsing Geometry...")
				vl=_get_child(e,"Vertices")["data"][0]
				nl=_get_child(_get_child(e,"LayerElementNormal"),"Normals")["data"][0]
				uvl=_get_child(_get_child(e,"LayerElementUV"),"UV")["data"][0]
				uvil=_get_child(_get_child(e,"LayerElementUV"),"UVIndex")["data"][0]
				il_=_get_child(e,"PolygonVertexIndex")["data"][0]
				i=0
				c=[]
				il=[]
				print(" "*bi+"Triangulating Polygons...")
				while (i<len(il_)):
					if (il_[i]<0):
						c+=[(~il_[i],i+0)]
						if (len(c)==3):
							il+=c
						else:
							tc=panda3d.core.Triangulator3()
							lvl=[]
							for n in c:
								lvl+=[n]
								tc.addPolygonVertex(tc.addVertex(*vl[n[0]*3:n[0]*3+3]))
							tc.triangulate()
							for n in range(0,tc.getNumTriangles()):
								il+=[lvl[tc.getTriangleV0(n)],lvl[tc.getTriangleV1(n)],lvl[tc.getTriangleV2(n)]]
						c=[]
					else:
						c+=[(il_[i],i+0)]
					i+=1
				print(" "*bi+"Merging Data...")
				g[0]+=vl
				g[1]+=nl
				g[2]+=uvl
				g[3]+=[(se[0]+(len(g[0])-len(vl))//3,se[1]+(len(g[1])-len(nl))) for se in il]
				g[4]+=[se+(len(g[2])-len(uvl))//3 for se in uvil]
				g[5]+=[e]
				g[6]+=[(len(g[3]),_get_child(_get_child(e,"LayerElementNormal"),"MappingInformationType")["data"][0])]
			elif (e["type"]=="Material"):
				print(" "*bi+"Parsing Material...")
				if (m!=None):
					raise RuntimeError("Duplicate Material!")
				print(" "*bi+"Merging Data...")
				m={"c":{"a":_get_prop70(_get_child(e,"Properties70"),"AmbientColor"),"d":_get_prop70(_get_child(e,"Properties70"),"DiffuseColor"),"s":_get_prop70(_get_child(e,"Properties70"),"SpecularColor")},"se":_get_prop70(_get_child(e,"Properties70"),"ShininessExponent")[0]}
			elif (e["type"]=="AnimationCurveNode"):
				print(" "*bi+"Parsing Default Offsets...")
				if (et=="Lcl Translation"):
					l[_name(k["name"])]["dx"]=_get_prop70(_get_child(e,"Properties70"),"d|X")[0]
					l[_name(k["name"])]["dy"]=_get_prop70(_get_child(e,"Properties70"),"d|Y")[0]
					l[_name(k["name"])]["dz"]=_get_prop70(_get_child(e,"Properties70"),"d|Z")[0]
				elif (et=="Lcl Rotation"):
					l[_name(k["name"])]["drx"]=_get_prop70(_get_child(e,"Properties70"),"d|X")[0]
					l[_name(k["name"])]["dry"]=_get_prop70(_get_child(e,"Properties70"),"d|Y")[0]
					l[_name(k["name"])]["drz"]=_get_prop70(_get_child(e,"Properties70"),"d|Z")[0]
				else:
					raise RuntimeError(et)
			else:
				raise RuntimeError(e["type"])
		return (l,ch,nr,g,m)
	def _read_deform(cl,ol,l,k,i):
		print(" "*i+f"Parsing Deform '{k['name']}'...")
		l[_name(k["name"])]["deform"]=({"indexes":_get_child(k,"Indexes")["data"][0],"weights":_get_child(k,"Weights")["data"][0]} if _get_child(k,"Indexes")!=None else {"indexes":[],"weights":[]})
		if (k["id"] in list(cl.keys())):
			for _,e in _get_refs(cl,ol,k["id"],-1):
				if (e["type"]=="Deformer"):
					l=_read_deform(cl,ol,l,e,i+2)
				elif (e["type"]=="Model"):
					continue
				else:
					raise RuntimeError(e["type"])
		return l
	def _write_mdl(f,k,i,mp):
		print(" "*i+f"Writing Model '{k['name']}' to File...")
		if ("children" not in list(k.keys())):
			k["children"]=[]
		if ("deform" not in list(k.keys())):
			k["deform"]={"indexes":[],"weights":[]}
		if ("dx" not in list(k.keys())):
			k["dx"]=0
			k["dy"]=0
			k["dz"]=0
		if ("drx" not in list(k.keys())):
			k["drx"]=0
			k["dry"]=0
			k["drz"]=0
		ti=k["deform"]["indexes"][:]
		tw=k["deform"]["weights"][:]
		k["deform"]["indexes"]=[]
		k["deform"]["weights"]=[]
		for j,e in enumerate(ti):
			k["deform"]["indexes"]+=mp[e]
			k["deform"]["weights"]+=[tw[j]]*len(mp[e])
		nm=_name(k["name"])
		f.write(struct.pack(f"<B{len(nm[:255])}sfB6fI{len(k['deform']['indexes'])}H{len(k['deform']['indexes'])}f",len(nm[:255]),bytes(nm[:255],"utf-8"),k["len"],len(k["children"]),k["dx"],k["dy"],k["dz"],k["drx"],k["dry"],k["drz"],len(k["deform"]["indexes"]),*k["deform"]["indexes"],*k["deform"]["weights"]))
		for e in k["children"]:
			_write_mdl(f,e,i+2,mp)
	print("Parsing Poses...")
	f.write(struct.pack("<B",len(pl)))
	for p in pl:
		print(f"  Parsing Pose '{p['name']}'...")
		l={}
		ch={}
		nr=[]
		g=[[],[],[],[],[],[],[]]
		m=None
		print("    Parsing Nodes...")
		for ok in p["children"]:
			if (ok["name"]=="PoseNode"):
				k=ol[_get_child(ok,"Node")["data"][0]]
				if (k["type"]=="NodeAttribute"):
					print(f"      Parsing Node Attribute '{k['name']}'...")
					if (_name(k["name"]) not in list(l.keys())):
						l[_name(k["name"])]={}
					print("      Merging Data...")
					l[_name(k["name"])]["len"]=_get_prop70(_get_child(k,"Properties70"),"Size")[0]
				elif (k["type"]=="Model"):
					l,ch,nr,tg,tm=_read_mdl(cl,ol,l,ch,nr,k,False,6)
					if (tm!=None and m!=None):
						raise RuntimeError("Duplicate Material!")
					if (tm!=None):
						m=tm
					print("      Merging Data...")
					for i,j in enumerate(tg):
						g[i]+=j
				else:
					raise RuntimeError(k["type"])
		print("    Parsing Deforms...")
		for k in g[5]:
			for _,e in _get_refs(cl,ol,k["id"],-1):
				l=_read_deform(cl,ol,l,e,6)
		print("    Creating Model Tree...")
		for k in [e for e in l.keys() if e not in nr]:
			l=_join(l,ch,k)
		l={k:v for k,v in l.items() if "len" in list(v.keys())}
		print("    Preprocessing Verticies...")
		dtl=[]
		il=[]
		vhl=[]
		lp=-1
		mp={}
		for i,k in enumerate(g[3]):
			if (i*100//len(g[3])>lp):
				print(f"      {i*100//len(g[3])}% Complete ({len(dtl)//STRIDE}v, {len(il)//3}i)...")
				lp=i*100//len(g[3])
			n=None
			for e in g[6]:
				if (i<=e[0]):
					if (e[1]=="ByPolygonVertex"):
						n=g[1][k[1]*3:k[1]*3+3]
					elif (e[1]=="ByVertice"):
						n=g[1][k[0]*3:k[0]*3+3]
			v=(*g[0][k[0]*3:k[0]*3+3],*n,*g[2][g[4][k[1]]*2:g[4][k[1]]*2+2])
			if (len(v)!=STRIDE):
				raise RuntimeError(str(v))
			if (hash(v) not in vhl):
				if (k[0] not in list(mp.keys())):
					mp[k[0]]=[]
				dtl+=v
				vhl+=[hash(v)]
				mp[k[0]]+=[vhl.index(hash(v))]
			il+=[vhl.index(hash(v))]
		print(f"      100% Complete ({len(dtl)//STRIDE}v, {len(il)//3}i)...\n    Writing To File...")
		nm=_name(p["name"])
		f.write(struct.pack(f"<B{len(nm)}sBII{len(dtl)+10}f{len(il)}H",len(nm),bytes(nm,"utf-8"),len(list(l.keys())),len(dtl)//STRIDE,len(il),*m["c"]["a"],*m["c"]["d"],*m["c"]["s"],m["se"],*dtl,*il))
		print("    Writing Models To File...")
		for k in l.values():
			_write_mdl(f,k,6,mp)



for fp in os.listdir("."):
	if (fp[-4:]==".fbx"):
		if (fp!="robot.fbx"):
			continue
		with open(fp,"rb") as f:
			dt=f.read()
		if (dt[:len(HEAD_MAGIC)]!=HEAD_MAGIC):
			continue
		print(fp)
		i=len(HEAD_MAGIC)+4
		gs=None
		ol=None
		cl=None
		df=None
		as_=None
		pl=[]
		while (i<len(dt)):
			i,e=_parse(dt,i)
			if (i is None):
				break
			if (e["name"]=="GlobalSettings"):
				gs=e
			elif (e["name"]=="Objects"):
				ol={}
				for k in e["children"]:
					ol[k["data"][0]]={"id":k["data"][0],"type":k["name"],"name":k["data"][1],"children":k["children"]}
					if (k["name"]=="AnimationStack"):
						as_=k["data"][0]
					if (k["name"]=="Pose"):
						pl+=[ol[k["data"][0]]]
			elif (e["name"]=="Definitions"):
				df={}
				for k in e["children"]:
					if (k["name"]=="ObjectType" and k["data"][0]!="GlobalSettings"):
						if (_get_child(k,"PropertyTemplate")!=None):
							df[k["data"][0]]=_get_child(_get_child(k,"PropertyTemplate"),"Properties70")["children"]
						else:
							df[k["data"][0]]=[]
			elif (e["name"]=="Connections"):
				cl={}
				for c in e["children"]:
					if (c["data"][2] not in list(cl.keys())):
						cl[c["data"][2]]=[]
					cl[c["data"][2]]+=[[c["data"][1],(None if len(c["data"])==3 else c["data"][3])]]
		for k,v in ol.items():
			ch=_get_child(v,"Properties70")
			kn=[]
			if (ch is None):
				v["children"]+=[{"name":"Properties70","children":[]}]
				ch=v["children"][-1]
			else:
				for e in ch["children"]:
					kn+=[e["data"][0]]
			for e in df[v["type"]]:
				if (e["data"][0] not in kn):
					kn+=[e["data"][0]]
					ch["children"]+=[e]
		off=([_get_prop70(_get_child(gs,"Properties70"),"TimeSpanStart")[0],_get_prop70(_get_child(gs,"Properties70"),"TimeSpanStop")[0]] if as_ is None else [_get_prop70(_get_child(ol[as_],"Properties70"),"LocalStart")[0],_get_prop70(_get_child(ol[as_],"Properties70"),"LocalStop")[0]])
		off[1]=_get_frame(off,off[1])
		if (as_!=None):
			with open(f"{fp[:-4]}.anm","wb") as f:
				f.write(struct.pack("<H",off[1]+1))
				_write_anim(f,off,cl,ol,_get_refs(cl,ol,0))
		if (len(pl)>0):
			with open(f"{fp[:-4]}.mdl","wb") as f:
				_write_poses(f,cl,ol,pl)
