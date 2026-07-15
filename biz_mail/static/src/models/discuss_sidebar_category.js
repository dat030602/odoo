/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'DiscussSidebarCategory',
    fields: {
        filteredCategoryItems: {
            compute(){
                let categoryItems = this.orderedCategoryItems;

                categoryItems =  categoryItems.sort((t1, t2) => {
                    if(t1.channel.isPinnedChannel && t2.channel.isPinnedChannel){
//                        if(t1.channel.noPinnedChannel < t2.channel.noPinnedChannel) {
                        if (t1.thread.lastInterestDateTime > t2.thread.lastInterestDateTime) {
                            return -1
                        } else{
                            return 1
                        }
                    }else if(t1.channel.isPinnedChannel && !t2.channel.isPinnedChannel){
                        return -1
                    }else if(!t1.channel.isPinnedChannel && !t2.channel.isPinnedChannel){
                        return 1
                    }
                });


                const searchValue = this.messaging.discuss.sidebarQuickSearchValue;
                const messageSearchValue = this.messaging.discuss.sidebarGroupsMessagesValue
                
                if (searchValue) {
                    const qsVal = searchValue.toLowerCase();
                    categoryItems = categoryItems.filter(categoryItem => {
                        const nameVal = categoryItem.channel.displayName.toLowerCase();
                        return nameVal.includes(qsVal);
                    });
                }else if(messageSearchValue){
                    categoryItems =  categoryItems.filter(item=>item.channel.hasBeenFound==true)
                }
                return categoryItems;
            }
        }
        
    },
});
