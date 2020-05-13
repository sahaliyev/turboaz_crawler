# turboaz_crawler

The script collects as many data as possible from turbo.az website which mostly has car advertisements on it. 
This script can be used by people who want to collect same data and play with it. 

The script consists of two main function extract_item() and parse_inner():
1. extract_item()
This function takes items on pagination pages. Like items in first page, items in second page and so on. 
1. parse_inner()
This function takes item url and parse inner page of that one item. 


It would be esay if you use this two function separately. However, you still able to use these function togather and since both function return dictionary we can easly concat them by using  "car.update(self.parse_inner(passed_url))" which you will see in 
extract_item() function. 

I collected data into mongodb since there is some data that cannot be structured such as phone numbers. In some ads there were more than one phone number which is basicly problematic to store in structured database. 
