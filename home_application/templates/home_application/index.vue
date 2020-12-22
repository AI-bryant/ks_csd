<template>
    <section>
        <bk-big-tree ref="tree"
            show-checkbox
            :data="data">
        </bk-big-tree>
    </section>
</template>
<script>
    import { bkBigTree, bkInput } from 'bk-magic-vue'
    export default {
        components: {
            bkBigTree,
            bkInput
        },
        data () {
            return {
                data: this.getNodes(null, 20, 2)
            }
        },
        methods: {
            getNodes (parent, childCount, deep) {
                const nodes = []
                for (let i = 0; i < childCount; i++) {
                    const node = {
                        id: parent ? `${parent.id}-${i}` : `${i}`,
                        level: parent ? parent.level + 1 : 0,
                        name: parent ? `${parent.name}-${i}` : `node-${i}`
                    }
                    if (node.level < deep) {
                        node.children = this.getNodes(node, 3, deep)
                    }
                    nodes.push(node)
                }
                return nodes
            }
        }
    }
</script>