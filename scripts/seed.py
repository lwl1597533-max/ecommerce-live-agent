import json
from pathlib import Path

catalog = [
 ('美妆','保湿面霜',99,{'容量':'50g','产地':'上海'},['甘油','透明质酸'],'日常保湿护理，使用前建议局部试用。'),
 ('食品','燕麦片',29.9,{'净含量':'500g','配料':'燕麦'},None,'冲泡食用，具体过敏原和营养信息以包装为准。'),
 ('3C','蓝牙耳机',199,{'蓝牙版本':'5.3','重量':'5g/只'},None,'适合日常听音乐和通话，实际体验受设备和环境影响。'),
 ('家居','收纳盒',39,{'材质':'PP','容量':'10L'},None,'适合整理桌面和衣柜物品，请根据实际空间选择。'),
]
products=[]
for category,name,price,specs,ingredients,desc in catalog:
    for i in range(6):
        products.append(dict(product_id=f'SKU{len(products)+1:03}',name=f'{name} 样例{i+1}',category=category,price=round(price+i*5,2),original_price=None,specs=specs,ingredients=ingredients,description=desc+' 本商品仅为开发测试模拟数据。',highlights=[f'{k}：{v}' for k,v in specs.items()],reviews=[],stock=100+i*20,promo=None,target_audience='有相关品类需求的消费者'))
path=Path(__file__).resolve().parent.parent/'data/mock_products.json'
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps({'products':products},ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Created {len(products)} sample products')
