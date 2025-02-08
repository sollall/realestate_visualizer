from tqdm import tqdm
import pandas as pd
import unicodedata

def lcf(str1, str2):
    dp = [[0] * (len(str2)+1) for i in range(len(str1)+1)]

    for i, vi in enumerate(str1):
        for j, vj in enumerate(str2):
            if vi == vj:
                dp[i+1][j+1] = dp[i][j] + 1
            else:
                dp[i+1][j+1] = max(dp[i+1][j], dp[i][j+1])
    #print(dp[len(str1)][len(str2)])

    ans = []
    i = len(str1) - 1
    j = len(str2) - 1
    while i >= 0 and j >= 0:
        if str1[i] == str2[j]:
            ans.append(str1[i])
            i -= 1
            j -= 1
        elif dp[i+1][j+1] == dp[i][j+1]:
            i -= 1
        elif dp[i+1][j+1] == dp[i+1][j]:
            j -= 1
    ans.reverse()
    return "".join(ans)

def extract_common_from_name(name_duplicated):
    ans=name_duplicated[0]
    for name in name_duplicated[1:]:
        ans=lcf(ans,name)
    
    return ans

def remove_duplication(data):

    #自分以外のすべてにlcfして、自分が再現できるものを集める　長すぎて...で省略されているものを除く
    #有効グラフを作成する　根側が名前が一番短く、実際の名前に近いと想定なるようにする
    names=data["name"].values
    directed_tree=[-1 for i in range(len(names))]
    for i in range(len(names)):
        if directed_tree[i]!=-1:
            continue

        name=data["name"].values[i]
        #nameを名前を含むものを抽出　すでに作成済みのデータの方からも一旦持ってくる
        #つまりname>=name_familyの名前になるはず
        #name_family = data[data["name"].apply(lambda x: lcf(name, x)==name)]
        name_family = list(map(lambda x: lcf(name, x),names))

        for j,common in enumerate(name_family):
            if i==j:
                continue
            if common==name:
                if directed_tree[j]==-1:
                    directed_tree[j]=i

    #有効グラフを使ってレコードの作成
    #rootまでたどっていって同じrootを持つ一家で詳細な情報をまとめて一つのレコードにする
    groups=[[] for i in range(len(directed_tree))]
    for i,root in enumerate(directed_tree):
        #初手からrootが-1だったらそれは始祖
        if root==-1:
            groups[i].append(i)
            continue
        
        while directed_tree[root]!=-1:
            root=directed_tree[root]
        groups[root].append(i)


    #同じ値段、同じ面積は同じ物件とみなす
    #同じとみなしたなかからより細かい住所とか、最も詳細なものを残す
    data_treated=[]
    for group in groups:
        if group==[]:
            continue

        samename=data.reset_index().loc[group]
        #name price address area age_years age_months
        # adressはここで取得しちゃお
        longest_address = samename.loc[samename['address'].apply(len).idxmax(),"address"]
        # 値段ごとに分解 
        for price in samename["price"].unique():
            price_group=samename[samename["price"]==price]

            for area in price_group["area"].unique():
                record=[
                    samename["name"].values[0],
                    price,
                    longest_address,
                    area,
                    samename["age_years"].values[0],
                    samename["age_months"].values[0],
                    samename["price per unit area"].values[0]
                ]

                data_treated.append(record)
                
    
    return data_treated

def remove_duplicated_from_data(df):

    #全角の英語を半角に変換するなど
    df["name"]=df["name"].apply(lambda x:unicodedata.normalize('NFKC', x))

    #まずは基準となる丁目までの住所を取得
    address_set=set(df["address"].values)

    short_addresses=[]

    for address in tqdm(address_set):
        #address_familyの中にaddressより長いものがあればうれしい
        address_family=df[df["address"].str.contains(address)]
        common=extract_common_from_name(address_family["address"].values)
        long_address_family=df[lambda df: df['address'].str.len() > len(common)]

        if len(long_address_family):
            short_addresses.append(common)

    records=[]

    for short_address in tqdm(short_addresses):
        local_df=df[df["address"].str.contains(short_address)]

        local_recodes=remove_duplication(local_df)

        records.extend(local_recodes)

    return pd.DataFrame(records,columns=df.columns)
