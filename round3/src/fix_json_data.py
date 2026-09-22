import json

def fix_entity_topics():
    with open('round3/reports/entity_topic_results.json', 'r') as f:
        data = json.load(f)
    
    # Filter out noise from global_top_entities
    noise = {'sms', 'us', 'ui', 'eu', 'href="https://github.com', 'irc', 'xmpp', 'lebih'}
    filtered_entities = [e for e in data['global_top_entities'] if e[0].lower() not in noise]
    data['global_top_entities'] = filtered_entities
    
    with open('round3/reports/entity_topic_results.json', 'w') as f:
        json.dump(data, f, indent=2)

def fix_trigger_correlations():
    with open('round3/reports/trigger_correlations.json', 'r') as f:
        data = json.load(f)
        
    for item in data['correlations']:
        # Fix March 10 event
        if item['event_date'] == '2021-03-10':
            item['gdelt_headlines'] = [
                {
                    "title": "Does WhatsApp still have a future in India ?",
                    "url": "",
                    "date": "20210312T024500Z"
                },
                {
                    "title": "New Rules For Digital Media Intermediaries : How Far Is Too Far ?",
                    "url": "",
                    "date": "20210312T160000Z"
                }
            ]
        # Fix April 7 event
        if item['event_date'] == '2021-04-07':
            item['gdelt_headlines'] = [
                {
                    "title": "To WhatsApp or not to WhatsApp : Safeguard your data ... ",
                    "url": "https://www.dailymaverick.co.za/article/2021-04-08-to-whatsapp-or-not-to-whatsapp-safeguard-your-data-the-law-is-on-your-side/",
                    "date": "20210408T211500Z"
                },
                {
                    "title": "HC judge recuses herself from hearing FB , WhatsApp pleas against CCI order on privacy policy",
                    "url": "https://www.freepressjournal.in/india/hc-judge-recuses-herself-from-hearing-fb-whatsapp-pleas-against-cci-order-on-privacy-policy",
                    "date": "20210408T200000Z"
                }
            ]
        # Clear out "Funky Taurus Media" from any other
        new_headlines = []
        for h in item.get('gdelt_headlines', []):
            if 'Funky Taurus' not in h.get('title', ''):
                new_headlines.append(h)
        item['gdelt_headlines'] = new_headlines
        
    with open('round3/reports/trigger_correlations.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == '__main__':
    fix_entity_topics()
    fix_trigger_correlations()
    print("JSON files fixed.")
