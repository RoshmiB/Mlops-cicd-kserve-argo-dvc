what vpc-cni addon does in eks :-

The vpc-cni (Amazon VPC Container Network Interface) is the core networking plugin for Amazon EKS that assigns real, native AWS VPC IP addresses directly to your Kubernetes Pods. [1, 2, 3, 4] 
By default, every Pod created in an EKS cluster gets an internal, isolated IP address. The vpc-cni addon changes this so that Pods are treated exactly like regular EC2 instances within your AWS virtual private network. [5, 6, 7, 8] 
## What the vpc-cni Addon Does

* Native VPC Integration: It connects Pods directly to your AWS VPC subnets and routing tables. This allows your Pods to communicate directly with other AWS resources (like RDS databases or S3 endpoints) without needing complex network setups. [9, 10, 11, 12, 13] 
* No Overlay Performance Costs: Traditional Kubernetes setups use an "overlay network" (like Calico or Flannel) which wraps network packets inside other packets, slowing down speeds. The vpc-cni uses direct routing, giving you near-line-rate network performance. [14, 15, 16, 17, 18] 
* Direct Security Group Enforcement: Because Pods have native VPC IPs, you can apply standard AWS Security Groups directly to individual Pods to control which network traffic is allowed in or out. [19, 20, 21, 22] 
* Saves Network Address Translation (NAT) Steps: Pods can talk to EC2 instances or other Pods in different clusters across the VPC without needing a NAT gateway or complex port mapping. [23, 24, 25] 

------------------------------
## How It Works Under the Hood

+-------------------------------------------------------------+

|                     AWS EC2 Worker Node                     |
|                                                             |
|   +-------------------+             +-------------------+   |
|   |       Pod A       |             |       Pod B       |   |
|   | (IP: 192.168.1.15)|             | (IP: 192.168.1.42)|   |
|   +---------+---------+             +---------+---------+   |
|             |                                 |             |
|             +----------------+----------------+             |
|                              |                              |
|   +--------------------------v--------------------------+   |
|   |         Elastic Network Interface (ENI)             |   |
|   |  Primary IP (Node) | Secondary IPs (Assigned to Pods)   |   |
|   +--------------------------+--------------------------+   |
+------------------------------|------------------------------+
                               |
                   +-----------v-----------+

                   |  Your AWS VPC Subnet  |
                   +-----------------------+


   1. Attaches Network Interfaces: The addon communicates with AWS to attach multiple Elastic Network Interfaces (ENIs) to your EC2 worker nodes.
   2. Allocates Secondary IPs: It requests a pool of secondary private IP addresses from your VPC subnet for each ENI.
   3. Wires the Pods: When a new Pod is scheduled on a node, the vpc-cni assigns one of those secondary IP addresses directly to that Pod. [26, 27, 28, 29] 

## One Major Catch: The "IP Exhaustion" Problem [30, 31] 
Because every Pod takes up a real AWS VPC IP, you can quickly run out of available IP addresses in your subnet if you deploy many small Pods. For example, a small EC2 instance type might only support a maximum of 12 or 20 IP addresses total. [32, 33, 34] 
Are you planning to deploy a high density of Pods on your EKS cluster? I can show you how to configure custom networking or prefix delegation to bypass this IP limit. [35, 36] 

[1] [https://repost.aws](https://repost.aws/knowledge-center/eks-cni-plugin-troubleshooting)
[2] [https://oneuptime.com](https://oneuptime.com/blog/post/2026-02-24-how-to-configure-istio-with-aws-vpc-cni/view)
[3] [https://www.ni.com](https://www.ni.com/docs/en-US/bundle/sle-it-admin/page/systemlink-enterprise-in-aws-eks.html)
[4] [https://dev.to](https://dev.to/aws-builders/navigating-aws-eks-with-terraform-understanding-eks-cluster-configuration-2f6o)
[5] [https://www.theodo.com](https://www.theodo.com/blog/how-to-deploy-an-elastic-kubernetes-service-eks-instance-on-aws)
[6] [https://medium.com](https://medium.com/@akashhardia/eks-pod-ip-address-assignment-explained-23646b301b59)
[7] [https://medium.com](https://medium.com/k8s-ebpf-tips/mastering-aws-vpc-cni-benefits-best-practices-troubleshooting-for-kubernetes-networking-56afddfa3b0f)
[8] [https://docs.gruntwork.io](https://docs.gruntwork.io/reference/modules/terraform-aws-eks/eks-cluster-control-plane/)
[9] [https://www.ni.com](https://www.ni.com/docs/en-US/bundle/sle-it-admin/page/systemlink-enterprise-in-aws-eks.html)
[10] [https://oneuptime.com](https://oneuptime.com/blog/post/2026-03-13-plan-aws-vpc-cni-chaining-cilium/view)
[11] [https://aws.plainenglish.io](https://aws.plainenglish.io/advanced-kubernetes-networking-concepts-with-eks-integration-b310dd874b7b)
[12] [https://www.linkedin.com](https://www.linkedin.com/pulse/integrating-aws-networking-kubernetes-using-cni-plugin-adamson-51y6c)
[13] [https://repost.aws](https://repost.aws/questions/QUyz_e6EbSROe0z0UyRM9a9A/create-an-eks-cluster-without-using-natgw-but-using-vpc-eks-endpoint)
[14] [https://learn.microsoft.com](https://learn.microsoft.com/en-us/azure/aks/concepts-network-cni-overview)
[15] [https://www.networkershome.com](https://www.networkershome.com/fundamentals/kubernetes-networking/kubernetes-cni-plugins/)
[16] [https://medium.com](https://medium.com/@jeetanshu/networking-in-multi-node-kubernetes-cluster-the-role-of-calico-dcd78367845e)
[17] [https://www.srodi.com](https://www.srodi.com/posts/kubernetes-networking-series-part-2/)
[18] [https://cloud.google.com](https://cloud.google.com/blog/products/networking/gke-network-interface-from-kubenet-to-ebpfcilium-to-dranet)
[19] [https://oneuptime.com](https://oneuptime.com/blog/post/2026-02-24-how-to-configure-istio-with-aws-vpc-cni/view)
[20] [https://gtsopour.medium.com](https://gtsopour.medium.com/aws-eks-maximum-number-of-pods-per-ec2-node-instance-bfbe658cecad)
[21] [https://www.sysdig.com](https://www.sysdig.com/learn-cloud-native/eks-security-best-practices-checklist)
[22] [https://overmind.tech](https://overmind.tech/types/eks-fargate-profile)
[23] [https://docs.cloud.google.com](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/gke-compare-network-models)
[24] [https://sigridjin.medium.com](https://sigridjin.medium.com/notes-on-eks-networking-i-aws-cni-e6d97e22dec6)
[25] [https://dev.to](https://dev.to/napicella/aws-networking-cheat-sheet-eip-eni-vpc-etc-139m)
[26] [https://akintola-lonlon.medium.com](https://akintola-lonlon.medium.com/aws-kubernetes-the-1-rule-you-need-to-master-before-going-to-production-628b75ba1b6a)
[27] [https://oneuptime.com](https://oneuptime.com/blog/post/2026-02-24-how-to-configure-istio-with-aws-vpc-cni/view)
[28] [https://docs.gruntwork.io](https://docs.gruntwork.io/reference/modules/terraform-aws-eks/eks-cluster-control-plane/)
[29] [https://engineering.salesforce.com](https://engineering.salesforce.com/optimizing-eks-networking-for-scale-1325706c8f6d/)
[30] [https://dev.to](https://dev.to/aws-builders/architecting-for-resilience-crafting-opinionated-eks-clusters-with-karpenter-cilium-cluster-mesh-part-1-1b9a)
[31] [https://www.reddit.com](https://www.reddit.com/r/kubernetes/comments/s6dg2n/cilium_on_eks_limitations/)
[32] [https://aws.plainenglish.io](https://aws.plainenglish.io/why-i-moved-from-aws-vpc-cni-to-cilium-a501ca529c08)
[33] [https://dev.to](https://dev.to/bansikah/amazon-eks-series-part-2-eks-architecture-and-core-components-36gk)
[34] [https://medium.com](https://medium.com/@octoz/aws-eks-one-more-step-towards-a-friendly-kubernetes-10d50368f67c)
[35] [https://repost.aws](https://repost.aws/articles/AR1uI6VjEDS_OF3ebAXh_5_Q/how-to-configure-custom-network-eniconfig-using-custom-labels-in-amazon-eks)
[36] [https://dev.to](https://dev.to/ravindukrs/a-production-ready-eks-deployment-with-iac-gitops-part-5-deploying-eks-cluster-29bn)


sure how to configure custom networking or prefix delegation to bypass this IP limit in eks :-

To bypass the EKS IP allocation limit, you can use either Prefix Delegation or Custom Networking. Choosing between them depends on whether your constraint is individual node limits or a complete lack of IP addresses in your corporate network space. [1, 2] 
------------------------------
## Option 1: Prefix Delegation (Easiest & Recommended)
Best for: When your VPC subnets have plenty of IPs, but your worker nodes are hitting their maximum Pod limits (e.g., small EC2 instances running out of ENI slots).
How it works: Instead of assigning individual secondary private IPs, the CNI assigns blocks of /28 prefixes (16 IPs per prefix) to the node's network interfaces. This multiplies your Pod density up to 110 Pods per node even on smaller instance sizes. [2, 3, 4, 5, 6] 
## Implementation Steps:

   1. Turn on Prefix Delegation in the aws-node DaemonSet:
   
   kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
   
   2. Configure Warm Targets to prevent the plugin from aggressively hogging too many large subnets in smaller environments:
   
   kubectl set env daemonset aws-node -n kube-system WARM_PREFIX_TARGET=1
   
   3. Deploy a new node group: Existing EC2 nodes cannot dynamically update their total max-pod values. You must create a new node group to inherit the prefix rules. [7, 8, 9, 10, 11] 

------------------------------
## Option 2: Custom Networking
Best for: When your primary VPC subnets are completely exhausted or crowded, and you need to shift Pod traffic into an isolated, larger, secondary IP range (like CG-NAT 100.64.0.0/10).
How it works: The EC2 host node retains its IP address in your core subnet, but secondary interfaces are built dynamically in entirely separate subnets dedicated exclusively to Pod traffic. [1, 12, 13] 
## Implementation Steps:

   1. Attach a secondary CIDR block to your AWS VPC via the AWS Console or CLI (e.g., 100.64.0.0/16).
   2. Create new private subnets within that secondary range, matching the exact Availability Zones (AZs) of your current cluster nodes.
   3. Enable Custom Networking in your cluster:
   
   kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
   
   4. Set the Availability Zone Labeling Rule so the CNI automatically matches nodes to the correct regional secondary subnet:
   
   kubectl set env daemonset aws-node -n kube-system ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
   
   5. Create an ENIConfig Custom Resource for each Availability Zone to direct traffic to your secondary subnets:
   
   # save as eni-config.yaml and run: kubectl apply -f eni-config.yamlapiVersion: crd.k8s.amazonaws.com/v1alpha1kind: ENIConfigmetadata:
     name: us-west-2a  # Must match the AZ name or node label exactlyspec:
     securityGroups:
       - sg-0123456789abcdef0  # Cluster node security group
     subnet: subnet-0abcdef1234567890  # Your newly created secondary subnet ID
   
   6. Recycle or scale your nodes to apply the configuration. [7, 12, 14, 15, 16, 17] 

------------------------------
## Comparison Matrix

| Feature [1, 2, 3, 13, 15, 17] | Prefix Delegation | Custom Networking |
|---|---|---|
| Primary Goal | Maximizes Pod count per single node. | Solves entire VPC subnet exhaustion. |
| IP Address Source | Existing node subnet. | New, independent secondary CIDR. |
| Complexity | Extremely low (single command). | Moderate (requires new subnets & CRDs). |
| Prerequisites | Nitro-based EC2 instances. | Secondary VPC block configuration. |

Would you like help calculating how many Pods you can run on your specific EC2 instance type once prefix delegation is switched on? [8] 

[1] [https://www.eksworkshop.com](https://www.eksworkshop.com/docs/networking/vpc-cni/custom-networking/)
[2] [https://www.youtube.com](https://www.youtube.com/watch?v=RBE3yk2UlYA)
[3] [https://www.eksworkshop.com](https://www.eksworkshop.com/docs/networking/vpc-cni/prefix/)
[4] [https://aws.amazon.com](https://aws.amazon.com/blogs/containers/amazon-vpc-cni-increases-pods-per-node-limits/)
[5] [https://aws-ia.github.io](https://aws-ia.github.io/terraform-aws-eks-blueprints/snippets/vpc-cni-custom-networking/)
[6] [https://www.reddit.com](https://www.reddit.com/r/kubernetes/comments/1ntnqgj/eks_auto_mode_missing_prefix_delegation/)
[7] [https://docs.aws.amazon.com](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html)
[8] [https://kubedemy.io](https://kubedemy.io/aws-eks-part-26-increase-vpc-cni-allocatable-ip-addresses)
[9] [https://kubedemy.io](https://kubedemy.io/aws-eks-part-26-increase-vpc-cni-allocatable-ip-addresses)
[10] [https://medium.com](https://medium.com/@mohamed.elmasary123/optimizing-pod-ip-allocation-in-aws-eks-with-amazon-vpc-cni-prefix-delegation-07d99004fdc2)
[11] [https://repost.aws](https://repost.aws/knowledge-center/eks-configure-cni-plugin-use-ip-address)
[12] [https://docs.aws.amazon.com](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html)
[13] [https://www.youtube.com](https://www.youtube.com/watch?v=htPxKBbGrMc)
[14] [https://docs.aws.amazon.com](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html)
[15] [https://www.truefoundry.com](https://www.truefoundry.com/docs/platform/custom-networking-in-eks)
[16] [https://aws.amazon.com](https://aws.amazon.com/blogs/containers/automating-custom-networking-to-solve-ipv4-exhaustion-in-amazon-eks/)
[17] [https://gonewaje.medium.com](https://gonewaje.medium.com/enable-prefix-delegation-in-aws-eks-for-better-ip-allocation-and-cost-efficiency-0188201ec590)


architecture diagram with sample ipss how the custiom networking works?

Here is an architectural diagram showing how Custom Networking routes traffic using a sample IP scheme.
In this scenario, your corporate network only has a small, crowded primary subnet (10.0.0.0/16), so we have attached a secondary CIDR block (100.64.0.0/16) specifically to host the Pods.
## Custom Networking Architecture Diagram

+-----------------------------------------------------------------------------------------+

|                                    AWS VPC (10.0.0.0/16)                                |
|                        Secondary CIDR Attached: 100.64.0.0/16                           |
|                                                                                         |
|  +---------------------------------------+   +---------------------------------------+  |
|  |    Primary Subnet (10.0.1.0/24)       |   |     Secondary Subnet (100.64.1.0/24)  |  |
|  |    (Crowded Corporate Range)          |   |     (Dedicated for EKS Pods Only)     |  |
|  +-------------------+-------------------+   +-------------------+-------------------+  |
|                      |                                           |                      |
|                      | (Allocates Host IP)                       | (Allocates Pod IPs)  |
|                      v                                           v                      |
|  +-----------------------------------------------------------------------------------+  |
|  | EKS EC2 Worker Node                                                               |  |
|  |                                                                                   |  |
|  |  +----------------------------------+       +----------------------------------+  |  |
|  |  | Pod 1                            |       | Pod 2                            |  |  |
|  |  | IP: 100.64.1.55 (Secondary Vpc)  |       | IP: 100.64.1.99 (Secondary Vpc)  |  |  |
|  |  +----------------+-----------------+       +----------------+-----------------+  |  |
|  |                   |                                          |                    |  |
|  |                   v                                          v                    |  |
|  |  +-----------------------------------------------------------------------------+  |  |
|  |  | aws-node DaemonSet (vpc-cni Plugin)                                         |  |  |
|  |  | Tracks ENIConfig CRD for Zone: us-west-2a                                   |  |  |
|  |  +-----------------------------------------------------------------------------+  |  |
|  |                   |                                          |                    |  |
|  |                   v                                          v                    |  |
|  |  +----------------------------------+       +----------------------------------+  |  |
|  |  | eth0 (Primary ENI)               |       | eth1 (Secondary ENI)             |  |  |
|  |  | Node IP: 10.0.1.10               |       | Subnet: 100.64.1.0/24            |  |  |
|  |  +----------------------------------+       +----------------------------------+  |  |
|  +-----------------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------------+

## Step-by-Step Traffic Flow Explainer

   1. Node Provisioning: The EC2 Worker Node boots up in the primary subnet and receives a standard host IP address via its primary network interface (eth0), which is 10.0.1.10.
   2. Configuration Reading: The aws-node plugin checks your Kubernetes configuration. It sees that custom networking is turned on and reads the ENIConfig file for that node's availability zone.
   3. Secondary Interface Creation: Instead of requesting more IP addresses from the crowded 10.0.1.0/24 subnet, aws-node tells AWS to attach a brand new network interface (eth1). It targets your custom, isolated subnet 100.64.1.0/24.
   4. Pod IP Assignment: When you deploy a microservice, Pod 1 and Pod 2 are scheduled on this node. The plugin grabs available secondary IPs directly from eth1 and wires them into the containers. The pods receive 100.64.1.55 and 100.64.1.99.
   5. Outbound Communication: When Pod 1 wants to talk to an RDS database or an on-premise service outside the cluster, the underlying Linux kernel on the EC2 host performs Source Network Address Translation (SNAT). It maps the packet source from the pod's IP (100.64.1.55) back to the node's host IP (10.0.1.10), ensuring the traffic flows smoothly across your corporate firewalls without any modifications.

Would you like the YAML manifest to configure the exact ENIConfig matching this setup?

