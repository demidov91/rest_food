xgettext -L Python --from-code=utf-8 ./rest_food/*/*.py -o rest_food/locale/_common.po

msgmerge rest_food/locale/ru/messages.po rest_food/locale/_common.po -o rest_food/locale/ru/LC_MESSAGES/messages.po --lang=ru
msgmerge rest_food/locale/be/messages.po rest_food/locale/_common.po -o rest_food/locale/be/LC_MESSAGES/messages.po --lang=be

rm rest_food/locale/_common.po